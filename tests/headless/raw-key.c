#define _GNU_SOURCE
#include <errno.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/mman.h>
#include <time.h>
#include <unistd.h>
#include <wayland-client.h>
#include <xkbcommon/xkbcommon.h>
#include "virtual-keyboard.h"

static struct wl_seat *seat;
static struct zwp_virtual_keyboard_manager_v1 *manager;
static void global(void *data, struct wl_registry *registry, uint32_t name,
                   const char *interface, uint32_t version) {
    (void)data; (void)version;
    if (!strcmp(interface, "wl_seat"))
        seat = wl_registry_bind(registry, name, &wl_seat_interface, 1);
    if (!strcmp(interface, "zwp_virtual_keyboard_manager_v1"))
        manager = wl_registry_bind(registry, name, &zwp_virtual_keyboard_manager_v1_interface, 1);
}
static void removed(void *data, struct wl_registry *registry, uint32_t name) {
    (void)data; (void)registry; (void)name;
}
static const struct wl_registry_listener listener = {global, removed};
static void fail(const char *message) { fprintf(stderr, "raw-key: %s\n", message); exit(1); }
static uint32_t milliseconds(void) {
    struct timespec t; clock_gettime(CLOCK_MONOTONIC, &t);
    return (uint32_t)(t.tv_sec * 1000 + t.tv_nsec / 1000000);
}
int main(int argc, char **argv) {
    if (argc < 2) fail("usage: raw-key +125 +3 -3 -125 (raw evdev codes)");
    struct wl_display *display = wl_display_connect(NULL);
    if (!display) fail("cannot connect to private Wayland display");
    struct wl_registry *registry = wl_display_get_registry(display);
    wl_registry_add_listener(registry, &listener, NULL);
    if (wl_display_roundtrip(display) < 0 || !seat || !manager) fail("virtual keyboard protocol or seat unavailable");
    struct xkb_context *context = xkb_context_new(XKB_CONTEXT_NO_FLAGS);
    struct xkb_rule_names names = {.layout = "us", .options = "ctrl:nocaps"};
    struct xkb_keymap *keymap = xkb_keymap_new_from_names(context, &names, XKB_KEYMAP_COMPILE_NO_FLAGS);
    if (!keymap) fail("US XKB keymap unavailable");
    char *text = xkb_keymap_get_as_string(keymap, XKB_KEYMAP_FORMAT_TEXT_V1);
    int fd = memfd_create("test-us-keymap", MFD_CLOEXEC);
    size_t length = strlen(text) + 1;
    if (fd < 0 || write(fd, text, length) != (ssize_t)length) fail("keymap fd failed");
    struct zwp_virtual_keyboard_v1 *keyboard = zwp_virtual_keyboard_manager_v1_create_virtual_keyboard(manager, seat);
    zwp_virtual_keyboard_v1_keymap(keyboard, WL_KEYBOARD_KEYMAP_FORMAT_XKB_V1, fd, length);
    if (wl_display_roundtrip(display) < 0) fail("keymap delivery failed");
    close(fd); free(text);
    struct xkb_state *state = xkb_state_new(keymap);
    for (int i = 1; i < argc; ++i) {
        char *end; errno = 0;
        unsigned long code = strtoul(argv[i] + 1, &end, 10);
        if ((argv[i][0] != '+' && argv[i][0] != '-') || !argv[i][1] || *end || errno || code > 767)
            fail("expected +evdev_code or -evdev_code in range 0..767");
        int down = argv[i][0] == '+';
        zwp_virtual_keyboard_v1_key(keyboard, milliseconds(), code, down);
        xkb_state_update_key(state, code + 8, down ? XKB_KEY_DOWN : XKB_KEY_UP);
        zwp_virtual_keyboard_v1_modifiers(keyboard,
            xkb_state_serialize_mods(state, XKB_STATE_MODS_DEPRESSED),
            xkb_state_serialize_mods(state, XKB_STATE_MODS_LATCHED),
            xkb_state_serialize_mods(state, XKB_STATE_MODS_LOCKED),
            xkb_state_serialize_layout(state, XKB_STATE_LAYOUT_EFFECTIVE));
        if (wl_display_roundtrip(display) < 0) fail("key delivery failed");
        usleep(20000);
    }
    zwp_virtual_keyboard_v1_destroy(keyboard);
    wl_display_roundtrip(display);
    xkb_state_unref(state); xkb_keymap_unref(keymap); xkb_context_unref(context);
    wl_registry_destroy(registry); wl_display_disconnect(display);
    return 0;
}
