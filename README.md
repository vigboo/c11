# Лабораторный стенд: Docker + межсетевой экран (nftables)

Этот стенд разворачивает изолированную «маленькую компанию» на Docker с несколькими сегментами сети, межсетевым экраном и базовыми сервисами (WAF, веб‑сервер, почта, DNS, файловый сервер, клиенты и рабочая станция).

Основная идея — отработать маршрутизацию между подсетями, публикацию портов, фильтрацию и NAT на nftables, а также типовые проверки доступности сервисов.

## Состав и сети

- Сегменты L3 (Docker bridge):
  - `users_net` — 192.168.1.0/24 (клиенты)
  - `dmz_net` — 192.168.2.0/24 (WAF/веб)
  - `servers_net` — 192.168.0.0/24 (инфраструктурные сервисы)
  - `uplink_net` — внешний/хостовой доступ (bridge без фиксированного адреса)
- Межсетевой экран `fw` выступает маршрутизатором между всеми внутренними сетями и «uplink`». Адреса шлюза в сегментах: 192.168.1.254, 192.168.2.254, 192.168.0.254.
- Публикация портов с хоста (docker-compose):
  - SSH: `2221->fw`, `2222->app_nginx`, `2223/2227/2228->app_empty*`
  - RDP демо: `6666->app_ubuntu:3389`
  - Проксируемые сервисы через `fw` (DNAT): HTTP `80->bunkerweb(192.168.2.20)->app_nginx(192.168.2.10)`, SMTP `25->srv_mailcow(192.168.0.20)`

## Что где лежит

- `docker-compose.yml` — описание всех сервисов/сетей и публикации портов
- `fw/` — контейнер межсетевого экрана
  - `fw/Dockerfile` — образ на Alpine (`nftables`, `iptables`, `iproute2`, `sshd`)
  - `fw/start.sh` — включение `ip_forward`, загрузка правил nft, настройка SSH и маршрута по умолчанию
  - `fw/nftables.conf` — правила фильтрации и NAT:
    - `table inet fw` — `input`, `forward`, `output`, наборы внутренних сетей
    - `table ip nat` — DNAT для 80/25 и SNAT/masquerade для обратного пути/выхода в uplink
- `bunkerweb/` — WAF/реверс‑прокси, проксирует в `app_nginx`
- `www/` — статический контент для `app_nginx`
- `srv_mailcow/` — упрощённая почтовая служба (только для практики; без TLS по умолчанию)
- `srv_dns/` — CoreDNS конфигурация
- `srv_samba/` — файловый сервер (демо‐шары)
- `srv_wazuh/` — задел под мониторинг/безопасность (демо)
- `srv_ansible/` — хост для Ansible
- `app_empty*/` — легковесные «клиенты» (Alpine + SSH)
- `app_ubuntu/` — демо‑рабочая станция (XRDP/SSH, преднастройка почты)
- `ansible/`, `users.yml` — вспомогательные материалы

## Переменные окружения

Создайте файл `.env` (он исключён из Git) с паролями/настройками, например:

```
FW_PASSWORD=Passw0rd!
APP1_PASSWORD=Passw0rd!
APP2_PASSWORD=Passw0rd!
APP_UBUNTU_PASSWORD=Passw0rd!
ANSIBLE_PASSWORD=Passw0rd!
SAMBA_USER=student
SAMBA_PASSWORD=Passw0rd!
SAMBA_SHARE_NAME=Share
WAZUH_PASSWORD=Passw0rd!
```

При необходимости добавьте SMTP/DNS и иные параметры соответствующим сервисам.

## Запуск

Быстрый старт (Docker Desktop/Engine + Compose V2):

- Построить и поднять всё: `docker compose up -d`
  - Для большинства сервисов задан `depends_on: [ fw ]`, поэтому FW поднимается первым.
- Избирательно по слоям (если хотите наблюдать этапы):
  1) `docker compose up -d fw` — FW: включает `ip_forward`, загружает `nftables`, настраивает дефолтный маршрут
  2) `docker compose up -d srv_dns srv_samba srv_mailcow srv_wazuh` — базовая инфраструктура
  3) `docker compose up -d bunkerweb app_nginx` — DMZ и веб
  4) `docker compose up -d app_empty1 app_empty2 app_empty3 app_ubuntu srv_ansible` — клиенты/рабочая станция/Ansible

Остановка/пересоздание:
- Остановить: `docker compose down`
- Пересоздать конкретный сервис: `docker compose up -d --build <service>`

## Проверки доступности

- Из хоста к WAF (DNAT HTTP): `curl -v http://127.0.0.1:80`
- Из хоста к SMTP (DNAT): `nc -vz 127.0.0.1 25`
- Межсегментный ICMP: `docker exec app_empty1 ping -c1 192.168.2.10`
- DNS: `docker exec app_empty1 dig @192.168.0.24 darkstore.local`
- Порты на Windows‐хосте: `Get-NetTCPConnection -LocalPort 80,25 -State Listen`

## nftables: перезагрузка и динамика

- Вручную перезагрузить правила внутри `fw`:
  - Проверка синтаксиса: `docker exec fw nft -c -f /etc/nftables.conf`
  - Применить: `docker exec fw nft -f /etc/nftables.conf`
- Динамические наборы/карты:
  - Можно использовать `define`: `define INTERNAL4 = { 192.168.1.0/24, 192.168.2.0/24, 192.168.0.0/24 }`
  - Для NAT используйте наборы/карты в той же таблице `ip nat` или `define` (сеты из `inet fw` не видны в `ip nat`).
- Полезные команды:
  - `docker exec fw nft list ruleset`
  - `docker exec fw nft monitor trace` — трассировка прохода пакетов через правила

## Важные моменты по фильтрации и NAT

- `chain forward` — место, где разрешается межсетевой трафик. Рекомендуется явная `policy drop` и отдельные правила для `ct state established,related`, ICMP и нужных портов.
- DNAT для HTTP/SMTP в `table ip nat` (PREROUTING):
  - HTTP: перенаправление либо на `bunkerweb (192.168.2.20)`, либо (для внутренних источников) напрямую на `app_nginx (192.168.2.10)` — не забывайте делать правила взаимоисключающими или использовать `return` после первого `dnat`.
  - SMTP: `25 -> 192.168.0.20:25`.
- SNAT/masquerade в `POSTROUTING` обеспечивает возврат трафика через `fw` для DNAT‑флоу и исходящий трафик в uplink.
- `fw/start.sh` включает `net.ipv4.ip_forward=1` и подхватывает `nftables.conf` (с удалением `CR` для Windows‑монтированного файла), что устраняет проблемы несовместимых переводов строк.

## Настройка адреса «docker‑host» (шлюза)

- Для предсказуемых адресов шлюзов в пользовательских сетях укажите `gateway` в `docker-compose.yml` в разделе `networks.*.ipam.config`.
- Порядок сетей у сервиса `fw` влияет на то, через какой интерфейс приходят опубликованные с хоста порты. Чтобы DNAT не ломался при смене порядка интерфейсов, не «прибивайте» правила к `iifname` по номеру (`ethX`), а матчьте по порту/адресу назначения.

## Безопасность и оговорки

- Стенд учебный: параметры WAF/почты/SMB минимальны и не предназначены для интернета.
- Пароли/секреты храните в `.env` (в Git не попадает). Для примеров создайте `example.env` без чувствительных значений.

## Полезные команды

- Логи сервиса: `docker compose logs -f <service>`
- Инспект сети: `docker network inspect <network>`
- Маршруты внутри контейнера: `docker exec <service> ip route`
- Состояние портов: `docker exec <service> ss -lntup`