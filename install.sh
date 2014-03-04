#!/bin/bash

echo "would install"

clear

echo "==================================="
echo "Starting setup for new Xov.io pool."
echo "==================================="

# make a new copy of the config.py template
cp config.py.template config.py

# admin port
admin_port=$1
if [[ $OSTYPE == 'linux-gnu' ]]; then
  sed -i 's/ADMIN_PORT/'$admin_port'/g' config.py
else
  sed -i '' 's/ADMIN_PORT/'$admin_port'/g' config.py
fi

# random 32 character string generator
randstring() {
  len=32
  if [[ $OSTYPE == 'linux-gnu' ]]; then
    date +%s | md5sum | base64 | head -c $len ; echo
  else
    date +%s | md5 | base64 | head -c $len ; echo
  fi
}

# webapp2 secret_key
secret_key=$(randstring)
if [[ $OSTYPE == 'linux-gnu' ]]; then
  sed -i 's/SECRET_KEY/'$secret_key'/g' config.py
else
  sed -i '' 's/SECRET_KEY/'$secret_key'/g' config.py
fi

echo;
# contact form emails
read -p "Enter the email address to use for the contact form emails: " email
if [[ $OSTYPE == 'linux-gnu' ]]; then
  sed -i 's/CONTACT_EMAIL/'$email'/g' config.py
else
  sed -i '' 's/CONTACT_EMAIL/'$email'/g' config.py
fi

# aes and salt
aes_key=$(randstring)
if [[ $OSTYPE == 'linux-gnu' ]]; then
  sed -i 's/AES_KEY/'$aes_key'/g' config.py
else
  sed -i '' 's/AES_KEY/'$aes_key'/g' config.py
fi

salt=$(randstring)
if [[ $OSTYPE == 'linux-gnu' ]]; then
  sed -i 's/SALT/'$salt'/g' config.py
else
  sed -i '' 's/SALT/'$salt'/g' config.py
fi

# admin url setup

# job token generation
job_token=$(randstring)
if [[ $OSTYPE == 'linux-gnu' ]]; then
  sed -i 's/JOB_TOKEN/'$job_token'/g' config.py
else
  sed -i '' 's/JOB_TOKEN/'$job_token'/g' config.py
fi

echo;
# captcha input
echo "Visit http://www.google.com/recaptcha to get your public and private captcha keys."
read -p "Enter the public captcha key: " public_captcha
if [[ $OSTYPE == 'linux-gnu' ]]; then
  sed -i 's/PUBLIC_CAPTCHA/'$public_captcha'/g' config.py
else
  sed -i '' 's/PUBLIC_CAPTCHA/'$public_captcha'/g' config.py
fi
read -p "Enter the private captcha key: " private_captcha
if [[ $OSTYPE == 'linux-gnu' ]]; then
  sed -i 's/PRIVATE_CAPTCHA/'$private_captcha'/g' config.py
else
  sed -i '' 's/PRIVATE_CAPTCHA/'$private_captcha'/g' config.py
fi

echo;
# google analytics setup
echo "Visit http://www.google.com/analytics to get your GA code."
read -p "Enter the GA code: " ga_code
if [[ $OSTYPE == 'linux-gnu' ]]; then
  sed -i 's/GA_CODE/'$ga_code'/g' config.py
else
  sed -i '' 's/GA_CODE/'$ga_code'/g' config.py
fi

# long ass key
rand_key=$(randstring)
if [[ $OSTYPE == 'linux-gnu' ]]; then
  sed -i 's/RAND_KEY/'$rand_key'/g' config.py
else
  sed -i '' 's/RAND_KEY/'$rand_key'/g' config.py
fi

echo;
# app id setup for appengine
echo "Remember, your app needs to support federated logins on AppEngine!"