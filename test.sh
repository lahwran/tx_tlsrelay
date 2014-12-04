#!/usr/bin/env bash
# This file is licensed MIT. see license.txt.
# warning: I'm bad at bash. this is a bit hacky

# set up
set -m  # job control
set -e  # fast abort
function cleanup() {
    set +e
    for job in `jobs -p`; do
        kill -9 $job
    done
}
trap cleanup EXIT
export PYTHONUNBUFFERED=True
BASEPORT=5000

# reset and start relay
coverage erase
coverage run --rcfile=.coveragerc -p bin/tx_tlsrelay $BASEPORT --port-count 2 &
relaypid="$!"
sleep 0.5

function serve() {
    rm /tmp/address >&/dev/null || true
    coverage run --rcfile=.coveragerc -p "$@" > /tmp/address &
    secondtolastpid="$lastpid"
    lastpid="$!"
    sleep 2
    hostname="$(cat /tmp/address | sed 's/:.*$//')"
    port="$(cat /tmp/address | sed 's/^.*://')"
}
function stopserver() {
    set +e
    kill -INT "$lastpid"
    wait "$lastpid"
    set -e
}
function stopserver2() {
    set +e
    kill -INT "$secondtolastpid"
    wait "$secondtolastpid"
    set -e
}

function app_nc () {
    python -m tx_tlsrelay.tls_netcat -k application_certs "$@"
}

serve bin/relayed_echoserver localhost $BASEPORT
echo "--- expect to see 'hello world':"
(echo "hello world"; sleep 2) | app_nc $hostname $port
echo "---"; echo
stopserver

serve bin/relayed_echoserver localhost $BASEPORT
echo "--- expect to see 'resumed':"
kill -STOP $lastpid
echo "hello world" | app_nc $hostname $port
kill -CONT $lastpid
(echo "resumed"; sleep 2) | app_nc $hostname $port
echo "---"; echo
stopserver

echo "--- expect to see 'no controller linked':"
sleep 2 | nc $hostname $port
echo
echo "---"; echo

serve bin/relayed_echoserver localhost $BASEPORT
echo "--- expect to see 'hi!' once every second, three times:"
(for x in 1 2 3; do echo "hi!"; sleep 1; done) | app_nc $hostname $port
echo "---"; echo
stopserver

echo "--- expect to see a RelayFullError and a failure to kill a process"
serve bin/relayed_echoserver localhost $BASEPORT
serve bin/relayed_echoserver localhost $BASEPORT
stopserver2
stopserver
echo "---"; echo

kill -INT "$relaypid"
wait "$relaypid"

coverage combine
coverage html --omit="ve/*"
