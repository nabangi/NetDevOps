#### bin/bash
# Alpine server intital setup

`echo "hostname" > /etc/hostname`

#### To activate hostname

`hostname -F /etc/hostname`

#### To Configure Network

Edit 

`/etc/network/interfaces`

```
auto eth0

iface eth0 inet static
        address 192.168.1.150/24
        gateway 192.168.1.1
```
 
`Service Network Restart`

Edit

`/etc/ssh/sshd_config`

```
cat > /etc/apk/repositories << EOF; $(echo)

http://dl-cdn.alpinelinux.org/alpine/v$(cat /etc/alpine-release | cut -d'.' -f1,2)/main
http://dl-cdn.alpinelinux.org/alpine/v$(cat /etc/alpine-release | cut -d'.' -f1,2)/community
http://dl-cdn.alpinelinux.org/alpine/edge/testing

EOF
```

#### Other commands

`apk updated`
`apk add openssh`
`rc-update add sshd`
`rc-status`
