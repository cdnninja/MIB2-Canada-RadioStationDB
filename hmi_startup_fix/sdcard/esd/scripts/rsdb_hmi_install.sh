#!/bin/sh

# esd rsdb_hmi_install.sh - Canada RSDB: place the HMI startup file (MU1316 only)
# Copies /mod/RSDB/hmi_startup.json from the SD card to /eso/hmi/lsd/hmi_startup.json,
# so the HMI starts the radio station database service. Changes nothing unless the
# unit is MU1316 and the unit does not already have that file.

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
echo "Canada RSDB - place HMI startup file"
echo ""

# unit version, read the same way as M.I.B. (config/BASICS)
SED="$VOLUME/apps/sbin/sed"
XXD="$VOLUME/apps/sbin/xxd"
E2P="on -f rcc /net/rcc/usr/apps/modifyE2P"
MUVERSION="MU$( ($E2P r 3B9 4 | $SED -rn 's/^0x\S+\W+(.*?)$/\1/p' | $SED -rn 's:\W*(\S\S)\W*:0x\1\n:pg' | $SED -rn '/^0x/p' | $XXD -r -p | $SED 's/[^a-zA-Z0-9_-]//g') 2>/dev/null )"
echo "Unit: $MUVERSION"

if [ "$MUVERSION" != "MU1316" ];then
	echo "ABORTED: this file is only for MU1316. Nothing was changed."
elif [ ! -f $SRC ];then
	echo "ABORTED: /mod/RSDB/hmi_startup.json not found on SD. Nothing was changed."
elif [ -f $DST ];then
	echo "ABORTED: the unit already has /eso/hmi/lsd/hmi_startup.json. Nothing was changed."
	BAK=$VOLUME/backup/hmi_startup.json.from_unit
	if [ ! -f $BAK ];then
		mount -uw $VOLUME/ 2>/dev/null
		mkdir -p $VOLUME/backup 2>/dev/null
		cp $DST $BAK 2>/dev/null
	fi
	[ -f $BAK ] && echo "The unit's file is saved on SD: /backup/hmi_startup.json.from_unit"
else
	mount -uw /net/mmx/mnt/app 2>/dev/null
	cp $SRC $DST 2>/dev/null
	sync
	if [ -f $DST ];then
		echo "HMI startup file placed. Reboot the unit to apply."
	else
		echo "ERROR: HMI startup file was NOT placed."
	fi
fi

echo ""
echo "You can go back now..."

trap 2

exit 0
