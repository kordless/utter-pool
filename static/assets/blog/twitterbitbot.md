# A Marketing Bot That Sells OpenStack Cloud Instances for Bitcoin on Twitter
The twitter user [@obitcoin](http://twitter.com/obitcoin) runs a bot I wrote to sell instances off my [OpenStack cluster](http://www.stackgeek.com/guides/gettingstarted.html) at home for Bitcoin.  You can ask it to reserve an instance for you and it will reply with a link to a Bitcoin address and qrcode on [blockchain.info](https://blockchain.info).  Once you pay for the instance, the bot will text you with the IPs.

It's the most ridiculous thing I've ever written for a marketing ploy, but it's a pretty cool way to [show off what I'm building](https://github.com/StackMonkey/utter-va/blob/master/README.md#welcome-to-utterio-and-stackmonkey) with StackMonkey and the Utter.io [coop-compute exchange framework](https://github.com/StackMonkey/utter-pool/blob/master/whitepaper.md).  While I'm not done writing code by a long shot, I am currently looking for [beta testers for the appliance](https://www.stackmonkey.com/appliances/new/). If you are interested, hit me up on Twitter [@kordless](http://twitter.com/kordless).

Here's a quick rundown on how to use the bot to buy an instance.  The first thing you'll need to do is build out a JSON template for booting the instance.  The StackMonkey [virtual appliance](https://github.com/stackmonkey/utter-va) utilizes instance callbacks that use a slightly modified JSON version of the [cloud-init](http://cloudinit.readthedocs.org/en/latest/topics/examples.html) format: 

    {
      "instance": {
        "dynamic_image_url": "http://download.fedoraproject.org/pub/fedora/linux/updates/20/Images/x86_64/Fedora-x86_64-20-20140407-sda.qcow2",
        "ssh_key": [
          "ssh-rsa AAAAB3NzaC1yc2EAAAABIwAAAQEAscVmmQi5zYCETV8o1OBO8clqszLiYqg4odrrOJQujm9Ez/c9A8k8i/d0DQJ77FLmBo7zC3BMDGhScZbE41KTMT7Qt6ap55F6YSbkbOXEPteORSWoVxjZDp/1mraCT6hYjeQI6yGIlHXpDfgOWU3xRG1Tp2PTXYQnfnx7L5Xr5BOmkWwXS+7ghBpmCzx1cn6/wNlXzu3ZTGW0wQqwpJBfRprpPvSkBqjpQ14wKsdSZv3AXzmO/lxRlCJUH8vLTJsa8jNAvIBtnRhR+Uei+VfKNHQ9ZYfI+F/pKm66JBlKwOflWIuf0mX3eg1ypZeejB4Ld2SQJS9t0cb8LN/rv24WBQ== kord@superman.local"
        ],
        "post_creation": [
          "#cloud-config",
          "hostname: stackmonkey-va",
          "manage_etc_hosts: true",
          "runcmd:",
          " - [ wget, &#34;http://goo.gl/KJH5Sa&#34;, -O, /tmp/install.sh ]",
          " - chmod 755 /tmp/install.sh",
          " - /tmp/install.sh"
        ]
      }
    }

You'll need to give it a dynamic image URL for the boot image.  The default one above is Fedora, which should work for a demo. [Here](http://download.fedoraproject.org/pub/fedora/linux/updates/20/Images/x86_64/Fedora-x86_64-20-20140407-sda.qcow2) [are](http://cloud-images.ubuntu.com/trusty/current/trusty-server-cloudimg-amd64-disk1.img) a [few](http://cloudhyd.com/openstack/images/cirros-0.3.0-x86_64-disk.img) [images](http://cloudhyd.com/openstack/images/centos60_x86_64.qcow2) that might work if you want something different.  You'll also need to change out the ssh key to your own.  ***That's all one string in a single element array, no line feeds.***

You should probably hack up the post creation strings a bit.  It would be fine if you just dropped the **runcmd** stuff entirely, unless you want to try to provision the machine with some code.

Once you are done with your edits, save them to a [Pastebin paste](http://pastebin.com/zX5fD6HY) and then click on [the raw link](http://pastebin.com/raw.php?i=zX5fD6HY) at the top left of the Pastebin page.

Now tweet the following, substituting your Pastebin raw URL for mine:

    @obitcoin !instance ^http://pastebin.com/raw.php?i=zX5fD6HY
    
The bot should reply within in a minute or so:

    . @kordless send 0.000010 BTC/hour to blockchain.info/address/1AdQLY… in next 5 mins to start ~smi-xckfqkq9.
    
Click on the link to navigate to Blockchain.info's page, where you'll see a QRcode and the Bitcoin address:

[![blockchain](/assets/blog/images/blockchain_thumb.png)](/assets/blog/images/blockchain.png)

Use your [Bitcoin client](https://coinbase.com/) to send in some 10s multiple of μBTC (millionth of a BTC) to the appliance.  I'd suggest 200-300 μBTC (about 25 cents) for a day's time or so, given you'll pay about 5 cents or so for the Bitcoin transaction itself.  I'll write more about how micro-transactions will work on StackMonkey in a subsequent post, but know these transaction fees won't apply at scale.  Multi-output transactions rock.

Once the appliance notices the payment, it starts the instance.  I haven't worried about confirmations as the instances are cheap.  Once the instance starts, you'll get another tweet, this time with the IPs:

    . @kordless ~smi-xckfqkq9 | ipv6: 2601:9:1380:af:f816:3eff:fedc:46e4 | ipv4: 10.0.47.3 | ipv4: None

Notice the lack of a public IPv4 address.  I only sell IPv6 instances out of my house as I only have one IPv4 address here.  [Other providers](http://rackspace.com/) won't have that limitation, and some will only have private IPv4 addresses.  I'd guess those will be cheaper, given they'd only be useful through an SSL tunnel.

Finally, if you want a status update, do the following:

    @obitcoin !status
    @obitcoin !status ~smi-xckfqkq9


**Caveats**: If an instance expires, you won't get notified when it is suspended, although you can ask for status on it and see the time and make payments to relight it.  Also, people can see your IPv6 address, so I'll need to fix that up to use DMs.

Have fun!