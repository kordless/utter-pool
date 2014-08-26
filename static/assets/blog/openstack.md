# OpenStack's Future is Going to the Blockchain
I wrote a rather lengthy blog post last week about how OpenStack's future depends on embracing Bitcoin.  I decided to delete it and write this post instead.

Last year, Randy Bias wrote a blog post titled [*OpenStack's Future Depends on Embracing Amazon. Now.*](http://www.cloudscaling.com/blog/cloud-computing/openstack-aws/)  Bluntly, I'm not a big of Amazon's AWS.  Haven't been for a while for a bunch of reasons which all deal with trust.  Still, I believe that people should make their own choices about the infrastructure they use.  If I can be helpful educating them on my experience with AWS, and what we know about the system they run, then I will attempt to do so in a fair and balanced way.

That's where OpenStack comes in for me.  I'm a *HUGE FAN* of OpenStack and highly recommend companies consider using it instead of or in addition to AWS.  StackMonkey/Utter.io constitutes 100% of my professional life now and represents a cummulation of work for me that has spanned 15 years of thinking and building a cooperative Open Source global cloud. OpenStack is required to pull this off and the more people that use OpenStack, the better. As such, I'm taking all threats to its success seriously.

So, when Randy said he thought "elements" of the community have unfairly positioned OpenStack *against* AWS, it seriously upset me because a) I don't trust AWS and b) I love OpenStack.  Having a situation where you hate something that threatens something you love will cause most people to react with anger.  This anger is usually directed toward the person that triggered the response.

I actually don't know Randy at all. A few people that know both of us have told me he's awesome. I respect the hell out him simply because he's an entrepreneur that has to be beholdant to a board, his employees and his customers. I really have no justification for being angry at Randy because he's simply being practical and pointing out what he feels is right for OpenStack and, assumably, the strategic position he takes for his company.

Grumbling about someone else's position on something doesn't elevate your own position on the topic. Generally, the lesson is if you don't like a solution, come up with a better solution!  

I think I have an idea that can help provide a better solution than depending on Amazon for our success.  It involves using the Bitcoin blockchain.

## The Bitcoin Federation
It was nearly a month after getting seriously into Bitcoin (meaning I mined Dogecoin on servers under my house) that I realized cryptocurrencies could handily solve the problem of implementing a global Federation.  For the less cloudy of you, WikiPedia describes a Federation as "multiple computing and/or network providers agreeing upon standards of operation in a collective fashion". Essentially we're talking about a global compute cloud that is completely interoperable with every other bit of the compute cloud, including the bits that run private clouds.  

The federation essentially represents the holy grail of computing.

By the way, notice the *multiple provider* comment in there.  Did you know that Amazon owne 85% of the public cloud market last year?  AWS ran all that out of 8 data centers!  Folks, that's a *single* provider running 85% of this world's public 'cloud' in 8 measlily datacenters using **closed source code**.  Meh.  Consider me seriously disappointed.  I was also promised flying cars.

Federation has always been what most consider to be the **third rail** of cloud computing; everyone wants it bad and most die trying to get it. Companies want a crack at Federation because it basically gives you global access to ALL markets.  Those markets are a big deal to every single tech company on the planet, which is why you see so many of them 'all in' on Openstack. OpenStack is the world's best shot at a globally federated cloud!

Except, it's not.  It's falling down because there isn't a clear and cohesive message explaining how OpenStack is going to solve federation.  Instead, we are simply pointing at the current best effort, and that's Amazon.  Where is it going you guys?

This is where you say "where is it going Kord?".

## To the Moon
It's going to the fucking moon, that's where.  A guy named Eric Martiandale, who works at Bitpay, wrote a cool little thing called Bitauth a month or so ago.  I haven't used it, but you can review the comments that were posted on HackerNews about it when it came out.  In theory, it provides a way to authenticate yourself to an instance, like you would with an SSH key, but uses your Bitcoin private key instead.  I'm sure there are details to work out like integrating a plugin for ssh libraries and such.

Now, if you've read what I'm doing with StackMonkey and the Utter.io framework, you'll see that Bitpay thing Eric did becomes VERY interesting, very quickly.  It will allow a StackMonkey user to pay for an public instance and then **log into* the instance with the exact same key they paid with.  That a powerful thing.

The reason it's so powerful is multifold (which is what you want when you completely dominate a market) is because those keys can be the same keys that operate your private cloud.








