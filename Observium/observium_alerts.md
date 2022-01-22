# Observium Email Alerts and Alert Checkers

#### First backup config file

    `sudo cp config.php config.php.bk_`date +%Y%m%d%H%M`

Use your editor of choice to edit

`config.php` 

#### set it in similar format as this:

`$config['email']['from'] = "system@cool.com";`<br>
`$config['email']['backend'] = 'smtp';`<br>
`$config['email']['smtp_host'] = 'smtp.office365.com';`<br>
`$config['email']['smtp_port'] = 587;`<br>
`$config['email']['smtp_timeout'] = 10;`
`$config['email']['smtp_secure'] = 'tls';`
`$config['email']['smtp_auth'] = TRUE;`
`$config['email']['smtp_username'] = 'system@cool.com';`
`$config['email']['smtp_password'] = 'password';`

#### Install Sendmail if you already don't hae it running

Follow the steps in this link:

`https://www.cloudbooklet.com/how-to-install-and-setup-sendmail-on-ubuntu/`

also ensure you have the following setup

`sudo apt install openssl sasl2-bin`

`sudo service saslauthd start`

#### Configure Sendmail

Change the Sendmail main config

`sudo vi /etc/mail/sendmail.mc`

Add the line:

    `include(`/etc/mail/tls/starttls.m4')dnl`

below the line:

    `include(`/usr/share/sendmail/cf/m4/cf.m4')dnl`
