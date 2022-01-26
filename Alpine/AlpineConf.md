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
# Install KVM

####  Guest OS Configs
```
virt-install \
--virt-type=kvm \
--name centos7 \
--ram 2048 \
--vcpus=1 \
--os-variant=centos7.0 \
--cdrom=/var/lib/libvirt/boot/CentOS-7-x86_64-Minimal-2009.iso \
--network=bridge=virbr0,model=virtio \
--graphics vnc \
--disk path=/var/lib/libvirt/images/cnod1.qcow2,size=40,bus=virtio,format=qcow2
```
#### Other commands

`apk updated`<br>
`apk add openssh`<br>
`rc-update add sshd`<br>
`rc-status`<br>
