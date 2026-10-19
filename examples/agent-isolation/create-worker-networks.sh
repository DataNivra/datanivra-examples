#!/usr/bin/env bash
# Create the two container networks isolated DataNivra workers use for network sources and targets, and print
# (never apply) firewall rules that limit each network to the systems you name: forwarded traffic (DOCKER-USER)
# to the listed destinations only, and nothing to services on the Docker host itself (INPUT).
#
#   ./create-worker-networks.sh --source HOST:PORT [--source ...] --target HOST:PORT [--target ...] \
#       [--resolver IP ...]
#
# DNS: workers may resolve names only through the resolvers you list with --resolver (UDP/TCP 53); without one,
# no DNS is allowed and connection documents must use IP addresses. Prefer an internal resolver that answers only
# for your own zones: an open recursive resolver can carry data out in DNS queries.
#
# Review the printed rules, then apply them with your host firewall tooling. Stages without a network source or
# target never join these networks (they run with --network none).
set -euo pipefail
cli="${DATANIVRA_AGENT_ISOLATION_RUNTIME_CLI:-docker}"
sources=(); targets=(); resolvers=()
while [ $# -gt 0 ]; do
  case "$1" in
    --source) sources+=("${2:-}"); shift 2 ;;
    --target) targets+=("${2:-}"); shift 2 ;;
    --resolver) resolvers+=("${2:-}"); shift 2 ;;
    *) echo "unknown argument: $1" >&2; exit 64 ;;
  esac
done
for ip in "${resolvers[@]}"; do
  if ! [[ "$ip" =~ ^[0-9]{1,3}(\.[0-9]{1,3}){3}$ ]]; then echo "expected an IPv4 resolver, got '$ip'" >&2; exit 64; fi
done
for dest in "${sources[@]}" "${targets[@]}"; do
  if ! [[ "$dest" =~ ^[0-9]{1,3}(\.[0-9]{1,3}){3}(/[0-9]{1,2})?:[0-9]{1,5}$ ]]; then
    echo "expected IPv4[/prefix]:PORT, got '$dest'" >&2; exit 64
  fi
done
create() {  # name subnet
  if "$cli" network inspect "$1" >/dev/null 2>&1; then
    echo "network $1 exists"
  else
    "$cli" network create --driver bridge --subnet "$2" --opt com.docker.network.bridge.enable_icc=false "$1" >/dev/null
    echo "created network $1 ($2)"
  fi
}
rules() {  # chain subnet destinations...
  # A dedicated chain (allow list, then DROP) entered by a jump inserted at the TOP of DOCKER-USER, so an existing
  # RETURN or ACCEPT later in DOCKER-USER cannot let unmatched worker traffic through.
  local chain="$1" subnet="$2"; shift 2
  echo "iptables -N $chain 2>/dev/null || iptables -F $chain"
  for dest in "$@"; do
    echo "iptables -A $chain -d ${dest%:*} -p tcp --dport ${dest##*:} -j ACCEPT"
  done
  for ip in "${resolvers[@]}"; do
    echo "iptables -A $chain -d $ip -p udp --dport 53 -j ACCEPT"
    echo "iptables -A $chain -d $ip -p tcp --dport 53 -j ACCEPT"
  done
  echo "iptables -A $chain -m conntrack --ctstate ESTABLISHED,RELATED -j ACCEPT"
  echo "iptables -A $chain -j DROP"
  echo "iptables -C DOCKER-USER -s $subnet -j $chain 2>/dev/null || iptables -I DOCKER-USER 1 -s $subnet -j $chain"
  # DOCKER-USER sees forwarded traffic only; connections to the Docker host itself (e.g. via the bridge
  # gateway) traverse INPUT: deny them too, keeping only replies to connections the host opened.
  echo "iptables -N $chain-IN 2>/dev/null || iptables -F $chain-IN"
  echo "iptables -A $chain-IN -m conntrack --ctstate ESTABLISHED,RELATED -j ACCEPT"
  echo "iptables -A $chain-IN -j DROP"
  echo "iptables -C INPUT -s $subnet -j $chain-IN 2>/dev/null || iptables -I INPUT 1 -s $subnet -j $chain-IN"
}
create dn-sources 172.31.250.0/24
create dn-targets 172.31.251.0/24
echo
[ ${#resolvers[@]} -eq 0 ] && echo "# No --resolver given: workers on these networks get no DNS (use IP addresses)."
echo "# Review, then apply (sources). Afterwards verify: a listed source connects, 1.1.1.1:443 and"
echo "# 169.254.169.254:80 do not (e.g. docker run --rm --network dn-sources <image> -c '...')."
rules DN-ISO-SOURCES 172.31.250.0/24 "${sources[@]}"
echo "# Review, then apply (targets):"
rules DN-ISO-TARGETS 172.31.251.0/24 "${targets[@]}"
