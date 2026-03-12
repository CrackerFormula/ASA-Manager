ARG ALA_DATE=2026/03/12

# =============================================================================
# Stage 1: Arch base with ALA date pinning, multilib, and required packages
# =============================================================================
FROM archlinux:base AS arch-base
ARG ALA_DATE

# Pin pacman mirrors to Arch Linux Archive date
RUN echo "Server=https://archive.archlinux.org/repos/${ALA_DATE}/\$repo/os/\$arch" \
    > /etc/pacman.d/mirrorlist

# Enable multilib repository (append since base image has no commented section)
RUN printf '\n[multilib]\nInclude = /etc/pacman.d/mirrorlist\n' >> /etc/pacman.conf

# Initialize keyring and update packages
RUN pacman-key --init && \
    pacman-key --populate archlinux && \
    pacman -Sy --noconfirm archlinux-keyring && \
    pacman -Su --noconfirm

# Install all required packages
RUN pacman -S --noconfirm --needed \
    bash \
    curl \
    wget \
    git \
    unzip \
    tar \
    jq \
    sudo \
    shadow \
    glibc \
    gcc-libs \
    lib32-glibc \
    lib32-gcc-libs \
    lib32-libpulse \
    lib32-alsa-lib \
    lib32-openal \
    lib32-sdl2 \
    lib32-mesa \
    lib32-libxi \
    lib32-libxrandr \
    lib32-libxinerama \
    xorg-server-xvfb \
    xorg-xinit \
    python \
    python-pip \
    supervisor \
    net-tools \
    iproute2

# Generate en_US.UTF-8 locale
RUN sed -i 's/^#en_US.UTF-8 UTF-8/en_US.UTF-8 UTF-8/' /etc/locale.gen && \
    locale-gen

ENV LANG=en_US.UTF-8
ENV LC_ALL=en_US.UTF-8

# Create ark user with UID/GID 7777
RUN groupadd -g 7777 ark && \
    useradd -u 7777 -g 7777 -m -s /bin/bash -d /home/ark ark

# =============================================================================
# Stage 2: SteamCMD installation
# =============================================================================
FROM arch-base AS steamcmd

RUN mkdir -p /opt/steamcmd && \
    curl -fsSL "https://steamcdn-a.akamaihd.net/client/installer/steamcmd_linux.tar.gz" \
    | tar -xz -C /opt/steamcmd && \
    chmod +x /opt/steamcmd/steamcmd.sh

# Run steamcmd once to bootstrap and update itself
RUN mkdir -p /root/Steam /root/.steam
RUN /opt/steamcmd/steamcmd.sh +quit || true

# =============================================================================
# Stage 3: Proton-GE installation
# =============================================================================
FROM arch-base AS proton-ge

ARG PROTON_VERSION=GE-Proton9-27
ARG PROTON_URL=https://github.com/GloriousEggroll/proton-ge-custom/releases/download/${PROTON_VERSION}/${PROTON_VERSION}.tar.gz

RUN mkdir -p /opt/proton-ge && \
    curl -fsSL "${PROTON_URL}" \
    | tar -xz -C /opt/proton-ge

# =============================================================================
# Stage 4: Python venv setup (using Python 3.12 for PyO3 compatibility)
# =============================================================================
FROM python:3.12-slim AS python-venv

COPY requirements.txt /tmp/requirements.txt

RUN python -m venv /app/venv && \
    /app/venv/bin/pip install --upgrade pip && \
    /app/venv/bin/pip install --no-cache-dir -r /tmp/requirements.txt

# =============================================================================
# Final stage: assemble everything
# =============================================================================
FROM arch-base AS final

# Copy SteamCMD
COPY --from=steamcmd /opt/steamcmd /opt/steamcmd
COPY --from=steamcmd /root/.steam /root/.steam
COPY --from=steamcmd /root/Steam /root/Steam

# Copy Proton-GE
COPY --from=proton-ge /opt/proton-ge /opt/proton-ge

# Copy Python 3.12 runtime from the build stage (needed by the venv)
COPY --from=python-venv /usr/local/lib/python3.12 /usr/local/lib/python3.12
COPY --from=python-venv /usr/local/bin/python3.12 /usr/local/bin/python3.12
COPY --from=python-venv /usr/local/lib/libpython3.12.so* /usr/local/lib/
RUN ln -sf /usr/local/bin/python3.12 /usr/local/bin/python && ldconfig

# Copy Python venv
COPY --from=python-venv /app/venv /app/venv

# Copy supervisord config and entrypoint
COPY docker/supervisord.conf /etc/supervisor/supervisord.conf
COPY docker/entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

# Copy start_ark script
COPY app/scripts/start_ark.sh /app/scripts/start_ark.sh
RUN chmod +x /app/scripts/start_ark.sh

# Copy app source
COPY app/ /app/app/

# Ensure ark user owns /app
RUN chown -R ark:ark /app

# Expose ports
EXPOSE 7777/udp 7778/udp 27020/tcp 8080/tcp

ENTRYPOINT ["/entrypoint.sh"]
