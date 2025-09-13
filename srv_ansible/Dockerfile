FROM ubuntu:22.04

ENV DEBIAN_FRONTEND=noninteractive TZ=Etc/UTC

RUN apt-get update \
 && apt-get install -y --no-install-recommends \
    ansible \
    openssh-server \
    sshpass \
    python3 \
    python3-pip \
    sudo \
    iproute2 \
    ca-certificates \
 && rm -rf /var/lib/apt/lists/*

# Create user student with sudo
RUN useradd -m -s /bin/bash student \
 && echo "student ALL=(ALL) NOPASSWD: ALL" > /etc/sudoers.d/90-student \
 && chmod 0440 /etc/sudoers.d/90-student

EXPOSE 22

COPY start.sh /usr/local/bin/start.sh
RUN chmod +x /usr/local/bin/start.sh

WORKDIR /workspace

CMD ["/usr/local/bin/start.sh"]

