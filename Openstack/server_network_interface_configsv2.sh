#!/bin/sh
apt update 
apt install bridge-utils -y 

cp /etc/netplan/01-netcfg.yaml /etc/netplan/01-netcfg.yaml.bk_`date +%Y%m%d%H%M`
echo
echo
echo
echo "When giving IPs please follow this naming convention:"
echo "For host hostname: "
echo "          IPs: 10.40.300.31"
echo "               10.30.200.31"
echo "               10.20.100.31"
echo
echo "Note that the prefix is always an x+30 where x is the host number(svr1,svr2,svr3...etc)"
echo
read -p "Enter the management bridge IP (br-mgmt)of the server and append a CIDR(e.g 10.40.300.xxx/24): " brmgmt
read -p "Enter the storage bridge IP (br-storage)of the server and append a CIDR(e.g 10.30.200.xxx/24): " brstorage
read -p "Enter the vxlan bridge IP (br-vxlan)of the server and append a CIDR (e.g 10.20.100.xxx/24): " brvxlan
read -p "Enter the vlan bridge IP (br-vlan)of the server and append a CIDR (e.g 0.0.0.0/24): " brvlan
echo
cat > /etc/netplan/01-netcfg.yaml <<EOF
# This file describes the network interfaces available on your system
# For more informatiDontCh4ngeMe!on, see netplan(5).
network:
  version: 2
  renderer: networkd
  bridges:
        br-mgmt:
            addresses:
            - $brmgmt
            dhcp4: false
             gateway4: 10.40.300.1
            nameservers:
                addresses:
                - 8.8.8.8
                - 8.8.4.4
                search: []
            interfaces:
                - bond0
        br-storage:
            addresses:
            - $brstorage
            dhcp4: false
             gateway4: 10.30.200.1
            nameservers:
                addresses:
                - 8.8.8.8
                - 8.8.4.4
                search: []
            interfaces:
                - vlan.200
        br-vxlan:
            addresses:
            - $brvxlan
            dhcp4: false
             gateway4: 10.20.100.1
            nameservers:
                addresses:
                - 8.8.8.8
                - 8.8.4.4
                search: []
            interfaces:
                - vlan.100
        br-vlan:          
            interfaces:
                - vlan.22
  bonds:
        bond0:
            interfaces:
               - ens1f0
               - ens1f1
            parameters:
                mode: active-backup
  vlans:
      vlan.300:
          id: 300
          link: bond0
          dhcp4: false
          dhcp6: false
      vlan.300:
          id: 200
          link: bond0
          dhcp4: false
          dhcp6: false
      vlan.100:
          id: 100
          link: bond0
          dhcp4: false
          dhcp6: false
      vlan.22:
          id: 22
          link: bond0
          dhcp4: false
          dhcp6: false
  ethernets:
     ens2f0:
       dhcp4: yes
     ens1f1:
          dhcp4: false
     ens1f0:
          dhcp4: false
EOF
sudo netplan apply
echo "Network configuration complete"
echo
