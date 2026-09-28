#!/bin/sh

# esd rsdb_hmi_remove.sh - Canada RSDB: remove the HMI startup file
# Saves a copy of /eso/hmi/lsd/hmi_startup.json to the SD card, then deletes it from the
# unit. The HMI then uses its built-in startup settings again.

trap '' 2

export PATH=.:/proc/boot:/bin:/usr/bin:/usr/sbin:/sbin:/mnt/app/media/gracenote/bin:/mnt/app/armle/bin:/mnt/app/armle/sbin:/mnt/app/armle/usr/bin:/mnt/app/armle/usr/sbin
export LD_LIBRARY_PATH=/lib:/mnt/app/root/lib-target:/eso/lib:/mnt/app/usr/lib:/mnt/app/armle/lib:/mnt/app/armle/lib/dll:/mnt/app/armle/usr/lib
unset LD_PRELOAD

export GEM=1
VOLUME=/net/mmx/fs/sda0
SRC=$VOLUME/mod/RSDB/hmi_startup.json
DST=/net/mmx/mnt/app/eso/hmi/lsd/hmi_startup.json

echo -ne "M.I.B. - More Incredible Bash "
cat $VOLUME/VERSION
echo "Canada RSDB - remove HMI startup file"
echo ""

if [ -f $DST ];then
	mount -uw $VOLUME/ 2>/dev/null
	mkdir -p $VOLUME/backup 2>/dev/null
	cp $DST $VOLUME/backup/hmi_startup.json.removed 2>/dev/null && echo "Copy saved on SD: /backup/hmi_startup.json.removed"
	mount -uw /net/mmx/mnt/app 2>/dev/null
	rm -f $DST
	sync
	if [ -f $DST ];then
		echo "ERROR: HMI startup file was NOT removed."
	else
		echo "HMI startup file removed. Reboot the unit to apply."
	fi
else
	echo "No HMI startup file on the unit - nothing to remove."
fi

echo ""
echo "You can go back now..."

trap 2

exit 0
