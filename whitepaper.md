## Distributed Compute Exchange Whitepaper

### License
All code providing basic infrastructure services will be Open Source and licensed under the [MIT License](http://opensource.org/licenses/MIT).  Closed source code is welcomed and desired in both the purpose of accessing APIs externally and, more obviously, in the use of the virtual machines started within the exchange.  However, no closed source code which runs at the hypervisor level of the framework or which provides compute, network or storage will be promoted by the network or its affiliates.  These rules will be enforced using contracts established using coin technologies. Infrastructure is meant to be *distributed*, open, trustworthy and secure.

### Concept
The underlying concept is an instantiation of multiple cryptcoin operated 'compute pools', each of which are in turn powered by numerous [OpenStack](http://openstack.org) based micro cloud clusters.  These micro clouds are run by 'providers' and are managed remotely through their respective 'compute pools'.  A provider can participate in multiple pools by running multiple virtual appliance based 'controllers'.

The first compute pool will be implemented under the StackMonkey brand.  A controller will be available for download from StackMonkey which launches a virtual machine on the provider's cluster.

Wildly distinct and uniquely optimized compute pools will be capable of providing various levels of compute type ([CPU](http://en.wikipedia.org/wiki/Central_processing_unit)/[GPU](http://en.wikipedia.org/wiki/Graphics_processing_unit)/[ASIC](http://en.wikipedia.org/wiki/Application-specific_integrated_circuit)), memory and storage speed, reliability, instance capacity sizes, OS images and deployment framework types, branding, community connectivity and more.  Diversification is encouraged and welcome in this project.  Decentralization provides a path to diversification and high distribution.

Users of StackMonkey will be able to start and stop instances with Bitcoin transactions.  No user account or authentication is needed.  Payment fraud for instances is eliminated by utilizing Bitcoin payment verification and Coinbase's service to initiate callbacks to the providers on receipt of payment.

![mockup](https://raw2.github.com/StackMonkey/utter-pool/master/mockup.png)

It is the intent of this project to create a fully distributed compute exchange which greatly minimizes the central control authority for server starts and access.  Put another way, this project aims to provide a bridge between crypto currency markets and the very thing that allows them to exist: compute.  

Commodity compute has arrived.

### Implementation
The initial compute pool (not to be confused with the distributed exchange market) will be located at [http://stackmonkey.com/](http://stackmonkey.com/) and will live on a tradiontally hosted infrastructure, for now.  StackMonkey provides low-cost, low-trust, low-reliability services for providing VM services to developers, hackers and other individuals who need transitionary type instances with little to no authentication required via the pool controller.  Providers with excess capacity who sign up for the StackMonkey pool should expect moderate returns on their participation.

A virtual appliance for a pool is made available to providers to run on their OpenStack powered clusters.  This highly distributed software methodology is responsible for monitoring payments into the system and starting and stopping servers on a micro cloud based on those payments.

A decentralized market exchange for the pools will later be created at [http://utter.io](http://utter.io/) utilizing its own crypto currency for exchanges of compute.  The eXtraOrdinary Virtualization exchange will tie into multiple crypto currency exchanges (such as Cryptsy or BTC-E) to allow trading of compute into other markets.

It is likely that utter.io will be powered by [Ethereum](http://ethereum.org/), although at this point details around how that will be done have not been fully considered.  If you have interest in working in developing this portion of concept further, please contact me at kordless@stackgeek.com.

### Operation
The project is currently comprised of three repositories: [utter-pool]() for running the transactional portions of the StackMonkey site, [utter-va](https://github.com/StackMonkey/utter-va/) which is used to launch a virtual appliance (VA) on the provider's cluster and [utter-exchange](https://github.com/StackMonkey/utter-exchange), where all the pool-operators exchange compute resources.  

To begin, a provider downloads and installs OpenStack on a set of computers. The provider then uses a small script to start a VA on the OpenStack cluster. This VA becomes responsible for listening to callbacks triggered from Coinbase's bitcoin callback service.  The following script will build a VA for the StackMonkey pool:

    #!/bin/bash
    wget http://goo.gl/KJH5Sa -O - | bash

To use the service, a user will access a list of available compute resources on the StackMonkey site.  Basic filtering will be provided to search by criteria including instance type/size, OS image type, compute costs, and location.

Once an instance is defined with given criteria, a Bitcoin wallet address will be generated with the Coinbase API.  A callback will be added to the address which represents the service provider's API endpoint for a VA on a given OpenStack cluster deployment.  The user will use this address to launch an instance by sending it Bitcoin.  Other currencies will be supported in the future through exchanges.

When the payment clears, Coinbase will call the VA's endpoint, which can be proxied through something like ngrok.com or similar.  At this point the VA will initiate an instance start on the OpenStack cluster and make a callback to the pool operator (in this case, StackMonkey) to communicate the instance's details for access.  

*Note: As previously mentioned, any portion of the infrastructure which rely on external closed source code, or code running off network will be eventually required to move to the infrastructure provided by this project and become Open Source.  This is done to ensure the trust integrity of the system.*

The pool operator will update a resource page created for the payment by the user with instance details.  Instances are managed by adding additional coin to the wallet address.  Wallets are drained as instances run and when a wallet is emptied, the instance is halted by the provider's VA.  Drips into wallets ensure servers remain running.

A trust system will eventually be built which allows for escrowed fund deposits.  If trust levels of a user account are high enough (by introducing this pay-for-trust concept) they will be allowed to start more instances.  Low trust level [wallet addreses](https://blockchain.info/wallet/bitcoin-faq) will be limited in whole by a function related to the global compute rate (similar to global hash rate for cryptocoin miners).  This function should provide a market price of anonymous server starts and work nicely with a system based on karma.

Hackers are encouraged to utilize the system for whatever purpose they deem important, but should consider the implications of their actions are being tied directly to the cost of starting instances for non-trusted entities.  Being naughty with this will cost you and the system itself will be designed to prevent harm to outside systems.

### Funding
StackMonkey, its employees and its investors expect to be rewarded accordingly for bringing this concept to fruition.  Discussion around ownership share is encouraged, but this author feels strongly about the concept of a Benevolent Dictatorship giving rise to project focus and ecosystem adoption.  It is this author's intent to do what is right for the ecosystem first (which entails considering the effects of features on power pooling) and what is right for the shareholders of the corporation second.

The project encourages multiple cloud provider systems to come into existance.  Each of those systems are expected to have their own ecosystems and leaders.  The utter.io exchange will be capable of extracting value through market making.

A governance board will be established which represents the interests of the utter.io project as a whole.  The StackMonkey corporation will be created as a seperate entity, and exist as a multi-national corporation to ensure fair and equal treatment from the various regions in which it operates.  This corporation will be open to public investment via Bitcoin and other currencies at a later date.

Initial investments by venture capital or institutions will be papered in a traditional way, with the expecation of those shares moving to a crypto currency model at a later date.  Post money valuation is set at US$10M.  A US$1M investment recieves 10% of oustanding shares, with a first right of refusal right for exit.

The implementation of this funding is open to discussion.  Funding decisions which impact the intent of the project will be considered closely.

Donations for the project can be made at 1JT1mQS74Ub8jyxQ81aKEeoyudSRX8RJTA. Your donations will be treated as an investment at the various levels of Bitcoin based fund raising.

**Kord Campbell**, Coder and Evangelist

