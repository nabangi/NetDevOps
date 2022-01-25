#bin/bash
#alpine server intital setup

vi /etc/ssh/sshd_config

cat > /etc/apk/repositories << EOF; $(echo)

http://dl-cdn.alpinelinux.org/alpine/v$(cat /etc/alpine-release | cut -d'.' -f1,2)/main
http://dl-cdn.alpinelinux.org/alpine/v$(cat /etc/alpine-release | cut -d'.' -f1,2)/community
http://dl-cdn.alpinelinux.org/alpine/edge/testing

EOF

 apk updated
 
apk add openssh
rc-update add sshd
rc-status
