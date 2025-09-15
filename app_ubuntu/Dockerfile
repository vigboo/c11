FROM ubuntu:22.04

ENV DEBIAN_FRONTEND=noninteractive \
    TZ=Etc/UTC

RUN apt-get update \
 && apt-get install -y \
    xrdp \
    xorgxrdp \
    xserver-xorg-core \
    x11-xkb-utils \
    openssh-server \
    dbus-x11 \
    sudo \
    iproute2 \
    samba-client \
    cifs-utils \
    plasma-desktop \
    konsole \
    libreoffice \
    curl \
    gnupg \
    ca-certificates \
    bzip2 \
    xz-utils \
    desktop-file-utils \
    python3 python3-venv python3-pip \
    p7zip-full \
    cron \
 && rm -rf /var/lib/apt/lists/*

# Install Google Chrome (Chromium-based) from official repo
RUN set -eux; \
    install -d -m 0755 /usr/share/keyrings; \
    curl -fsSL https://dl.google.com/linux/linux_signing_key.pub | gpg --dearmor -o /usr/share/keyrings/google.gpg; \
    echo "deb [arch=amd64 signed-by=/usr/share/keyrings/google.gpg] https://dl.google.com/linux/chrome/deb/ stable main" > /etc/apt/sources.list.d/google-chrome.list; \
    apt-get update; \
    apt-get install -y --no-install-recommends google-chrome-stable; \
    rm -rf /var/lib/apt/lists/*

# Install Thunderbird (tarball) to /opt/thunderbird and add launcher
RUN set -eux; \
    mkdir -p /opt; \
    curl -fsSL "https://download.mozilla.org/?product=thunderbird-latest&os=linux64&lang=ru" -o /tmp/thunderbird.tar.xz; \
    tar -xJf /tmp/thunderbird.tar.xz -C /opt; \
    ln -sf /opt/thunderbird/thunderbird /usr/local/bin/thunderbird; \
    rm -f /tmp/thunderbird.tar.xz; \
    printf '[Desktop Entry]\nType=Application\nName=Thunderbird\nExec=thunderbird\nIcon=thunderbird\nCategories=Network;Email;\nTerminal=false\n' > /usr/share/applications/thunderbird.desktop; \
    update-desktop-database >/dev/null 2>&1 || true

# Ensure ping is available (install separately to avoid any conflicts)
RUN apt-get update && apt-get install -y iputils-ping && rm -rf /var/lib/apt/lists/*

# Ensure XRDP uses XFCE by default
# Ensure XRDP listens on TCP and all interfaces
RUN awk 'BEGIN{in_g=0} \
    /^\[Globals\]/{in_g=1} \
    /^\[.*\]/{if($0!~"^\\[Globals\\]") in_g=0} \
    { \
      if(in_g && $0 ~ /^use_vsock=/){$0="use_vsock=false"} \
      if(in_g && $0 ~ /^#?address=/){$0="address=0.0.0.0"} \
      if(in_g && $0 ~ /^port=/){$0="port=3389"} \
      print \
    }' /etc/xrdp/xrdp.ini > /etc/xrdp/xrdp.ini.tmp \
 && mv /etc/xrdp/xrdp.ini.tmp /etc/xrdp/xrdp.ini \
 && sed -i '/^\[Xorg\]/,/^\[/{s/^lib=.*/lib=libxup.so/; s/^port=.*/port=-1/; s/^ip=.*/ip=127.0.0.1/}' /etc/xrdp/xrdp.ini \
 && printf 'allowed_users=anybody\n' > /etc/Xwrapper.config

# Listen on all interfaces (default is fine, but ensure no IPv6 only)
# Ensure the listening port is correctly set only in [Globals]; keep [Xorg] port=-1

EXPOSE 3389

# Email watcher tool
COPY tools/email_watcher.py /opt/tools/email_watcher.py
RUN chmod +x /opt/tools/email_watcher.py

# Install Dolpin
RUN apt-get update && apt-get install -y dolphin kio-extras

# Run start.sh
COPY start.sh /usr/local/bin/start.sh
RUN chmod +x /usr/local/bin/start.sh
RUN mkdir /mnt/Share
CMD ["bash", "/usr/local/bin/start.sh"]