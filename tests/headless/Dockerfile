FROM ubuntu:24.04@sha256:008173c23f95b170204355c12626cb5a965d779a7e1283b09e9cffbb1bf33ca3
ENV DEBIAN_FRONTEND=noninteractive
RUN apt-get update && apt-get install -y --no-install-recommends ca-certificates
COPY hyprland.sources /etc/apt/sources.list.d/hyprland.sources
RUN apt-get update && apt-get install -y --no-install-recommends \
    ca-certificates python3 dbus-daemon mesa-utils libgl1-mesa-dri \
    hyprland=0.56.2-1ppa2 libaquamarine14=0.15.1-1ppa1 \
    jq libnotify-bin grim fonts-dejavu-core \
    gcc pkg-config libwayland-dev libxkbcommon-dev wayland-protocols \
    && rm -rf /var/lib/apt/lists/*
ADD https://github.com/mkasberg/ghostty-ubuntu/releases/download/1.2.3-0-ppa1/ghostty_1.2.3-0.ppa1_amd64_24.04.deb /tmp/ghostty.deb
RUN echo '99eadff67bf1d5883655dd77eead3256ace3b29a8b77973a2e217a8ebb412609  /tmp/ghostty.deb' | sha256sum -c - \
    && apt-get update && apt-get install -y --no-install-recommends /tmp/ghostty.deb libc6-dev \
    && rm /tmp/ghostty.deb && rm -rf /var/lib/apt/lists/*
COPY virtual-keyboard.xml raw-key.c /build/
RUN cd /build && wayland-scanner client-header virtual-keyboard.xml virtual-keyboard.h \
    && wayland-scanner private-code virtual-keyboard.xml virtual-keyboard.c \
    && gcc -Wall -Wextra -Werror raw-key.c virtual-keyboard.c -o /usr/local/bin/raw-key $(pkg-config --cflags --libs wayland-client xkbcommon) \
    && rm -rf /build
RUN apt-get update && apt-get install -y --no-install-recommends \
    meson ninja-build libffi-dev libexpat1-dev libxml2-dev libdrm-dev \
    libpixman-1-dev libegl-dev libgles2-mesa-dev libgbm-dev libxcursor-dev wayland-utils \
    && rm -rf /var/lib/apt/lists/*
# Pinned mirrors of upstream release commits, not moving branches.
ADD --checksum=sha256:98945aa2f0c73c38a6fc2dde83865c09269a32fac7d0e7982120d990f78e46f6 https://github.com/wayland-mirror/wayland/archive/a9fec8dd65977c57f4039ced34327204d9b9d779.tar.gz /tmp/wayland.tar.gz
ADD --checksum=sha256:55a35ddb63fb617cfd68dc1093643741c2b3925a9a093e7f8e04e7336aa47ca6 https://github.com/wleithauser/wlroots-mirror/archive/cda69b696d65a53d5d5e75dfed059a3803e0d700.tar.gz /tmp/wlroots.tar.gz
ENV PKG_CONFIG_PATH=/usr/local/lib/pkgconfig
RUN mkdir /tmp/build && cd /tmp/build && tar -xf /tmp/wayland.tar.gz \
    && meson setup wayland-build wayland-a9fec8dd65977c57f4039ced34327204d9b9d779 --prefix=/usr/local --libdir=lib -Dtests=false -Ddocumentation=false \
    && ninja -C wayland-build install && ldconfig \
    && tar -xf /tmp/wlroots.tar.gz \
    && cd wlroots-mirror-cda69b696d65a53d5d5e75dfed059a3803e0d700 \
    && sed -i 's/wlr_compositor_create(server.wl_display, 5,/wlr_compositor_create(server.wl_display, 6,/; s/wlr_xdg_shell_create(server.wl_display, 3)/wlr_xdg_shell_create(server.wl_display, 6)/' tinywl/tinywl.c \
    && meson setup build --prefix=/usr/local --libdir=lib --wrap-mode=nofallback -Dc_std=c11 \
       -Dbackends=[] -Drenderers=gles2 -Dallocators=gbm -Dsession=disabled \
       -Dxwayland=disabled -Dcolor-management=disabled -Dlibliftoff=disabled -Dexamples=true \
    && ninja -C build tinywl/tinywl libwlroots-0.18.so \
    && meson install -C build --no-rebuild \
    && install build/tinywl/tinywl /usr/local/bin/tinywl \
    && ldconfig && pkg-config --modversion wayland-server wlroots-0.18 > /bootstrap-versions.txt \
    && sha256sum /tmp/wayland.tar.gz /tmp/wlroots.tar.gz > /bootstrap-source-sha256.txt \
    && rm -rf /tmp/build /tmp/wayland.tar.gz /tmp/wlroots.tar.gz
RUN dpkg-query -W > /image-packages.txt
USER 1000:1000
ENTRYPOINT ["python3", "/source/tests/headless/session.py"]
