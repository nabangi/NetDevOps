# Cumulus Linux WhiteBox Switch Install Quick Start Guide

### Prepare usb bootable
    
#### Preferrably format usb in FAT32 then mount image as follows
    
```
linuxpc:~$ sudo mkdir /mnt/usb

linuxpc:~$ sudo mount /dev/sdb1 /mnt/usb

linuxpc:~$ sudo cp cumulus_linux.bin /mnt/usb/cumulus_linux.bin

linuxpc:~$ sudo umount /mnt/usb
```

#### Use Linux Screen for Console Access
    
    `sudo screen /dev/ttyUSB0 115200` 

## Mount USB in Switch

From Boot Menu to select "BOOT ONIE (Rescue Mode)

    `ONIE:/ # onie-discovery-stop`

#### Then plug in usb drive with desired Image

create a mount location for it

    `ONIE:/ # mkdir /mnt/media`

Validate the specific file path

    `ONIE:/ # blkid`
  
#### Use vfat option for the mount since we formatted using FAT32

    `ONIE:/ # mount -t vfat /dev/sdb1 /mnt/media`

Now we install the OS from the mounted USB

    `ONIE:/ # onie-nos-install /mnt/media/<cumulus-install-[PLATFORM].bin>`

#### After installation and reboot

Login with default credentials depending on the version you are using

## Quick Start
You can configure the eth0 port with a static IP or leave it to pick from DHCP as it will by default

`net add interface eth0 ip address 192.27.3.21/24` <br>
`net add interface eth0 ip gateway 192.27.3.1` <br>
`net pending` <br>
`net commit` <br>

`cat /etc/network/interfaces` 
```
auto eth0
iface eth0
    address 192.27.3.21/24
    gateway 192.27.3.1
```

### Configure the Hostname and Timezone

To change the hostname, run net add hostname, which modifies both the /etc/hostname and /etc/hosts files with the desired hostname.

cumulus@switch:~$ `net add hostname <hostname>`

cumulus@switch:~$ `net pending`

cumulus@switch:~$ `net commit`

To update the timezone, use NTP interactive mode:

    `sudo dpkg-reconfigure tzdata`

#### There are three ways to install the license onto the switch:

Copy the license from a local server. Create a text file with the license and copy it to a server accessible from the switch. On the switch, use the following command to transfer the file directly on the switch, then install the license file:

cumulus@switch:~$ `scp user@my_server:/home/user/my_license_file.txt`

cumulus@switch:~$ `sudo cl-license -i my_license_file.txt`

Copy the file to an HTTP server (not HTTPS), then reference the URL when you run cl-license:

cumulus@switch:~$ `sudo cl-license -i <URL>`

Copy and paste the license key into the cl-license command:

cumulus@switch:~$ `sudo cl-license -i`
<paste license key>

Check that your license is installed with the cl-license command.

cumulus@switch:~$ `cl-license` 


# VOOIILLAAAAAA!!!!!
