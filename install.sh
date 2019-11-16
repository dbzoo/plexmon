#!/bin/sh
if [ `id -u` -ne 0 ]; then
    echo "sudo sh $0"
    exit
fi
sed "s#%PWD%#$PWD#" plexmon.service > /lib/systemd/system/plexmon.service
systemctl daemon-reload
systemctl enable plexmon.service
systemctl start plexmon.service
