## Distributed Compute Exchange Whitepaper

### License
All code providing basic infrastructure services will be Open Source.  Closed source code is welcomed and desired in both the purpose of accessing APIs externally and, more obviously, in the use of the virtual machines started within the exchange.  However, no closed source code which runs at the hypervisor level of the framework or which provides compute, network or storage will be promoted by the network or it's affiliates.  These rules will be enforced using contracts established using coin technologies. Infrastructure is meant to be open, trustworthy and secure.

### Concept
The underlying concept of this 'service' is a cryptcoin operated 'compute pool' each of which is in turn powered by numerous OpenStack based clusters.  These micro clouds are run by 'providers' and are managed remotely through their respective 'compute pools'.  A provider can participate in multiple pools by running multiple virtual appliance 'controllers'.

Wildly distinct and uniquely optimized compute pools will be capable of providing various levels of compute type (CPU/GPU/ASIC), memory and storage speed, reliability, instance capacity sizes, OS images and deployment framework types, branding, community connectivity and more.  Diversification is encouraged and welcome in this project.  Centralization gives way to diversification and distribution.

It is the intent of this project to create a fully distributed compute exchange which greatly minimizes the central control authority for server starts and access.

Put another way, this project aims to provide a bridge between crypto currency markets and the very thing that allows them to exist: compute.  Commodity compute has arrived.

### Implementation
The initial compute pool (not to be confused with the distributed exchange) will live at http://stackmonkey.com/ and will be hosted on Google Appengine.  StackMonkey will initially provide a low-cost, low-trust, low-reliability service providing VM services to developers, hackers and other individuals who need transitionary type instances.  Providers who sign up for the StackMonkey exchange should get comfortable with the concept of decentralized resource allocation and are encouraged to educate themselves on the coming decentralization revolution in in the computing and business markets.

Shit happens. The golden rule governs all feature sets and defines the code written for all aspects of the project.   We're building this for all humanity, and will make every attempt with our code to prevent pools of power from corrupting it.

A decentralized market exchange for the pools will later be created at http://xov.io or http://xov.bit (currently held by a .bit squater), perhaps utilizing something like Namecoin for storage.  The eXtraOrdinary Virtualization exchange will tie into multiple crypto currency exchanges (such as Cryptsy or BTC-E) and will likely need to create a crypto coin of its own used for trading into other currencies.

It is likely that xov.io/xov.bit will be powered by Ethereum, although at this point details around how that will be done have not been fully considered.  If you have interest in working in developing this portion of concept further, please contact me at kordless@stackgeek.com.

### Operation
The project is currently comprised of three repositories: this repository (xovio-pool) for running the transactional portions of the StackMonkey site, a project called xovio-va (https://github.com/StackMonkey/xovio-va/) which is used to launch a virtual appliance (VA) on the provider's cluster and lastly xovio-exchange, the place where all the pool-operators exchange compute resources.  

To begin, a provider downloads and installs OpenStack and the xov-va on a set of computers.  This VA becomes responsible for listening to callbacks triggered from blockchain.info's bitcoin callback service.

To use the service, a user will access a list of compute resources on the StackMonkey site.  Basic filtering will be provided to search by criteria including instance type/size, OS image type, compute costs, and location.

Once an instance is defined with given criteria, a Bitcoin wallet address will be generated with the Blockchain.info API.  A callback will be added to the address which represents the service provider's API endpoint for a VA on a given OpenStack cluster deployment.  The user will use this address to launch an instance by sending it Bitcoin.  Other currencies will be supported in the future through exchanges.

When the payment clears, Blockchain.info will call the VA's endpoint, which could be proxied through something like ngrok.com or similar.  At this point the VA will initiate an instance start on the OpenStack cluster and make a callback to the pool operator (in this case, StackMonkey) to communicate the instance's details for access.  

Note: Blockchain.info or similarly untilized services will eventually be required to move to the infrastructure provided by these distributed system to avoid single points of failure of existing external blockchain trust systems.

The pool operator will update a resource page created for the payment by the user with instance details.  Instances are managed by adding additional coin to the wallet address.  Wallets are drained as instances run and when a wallet is emptied, the instance is halted by the provider's VA.

A trust system will eventually be built which allows for escrowed fund deposits.  If trust levels of a user account are high enough (by introducing this pay-for-trust concept) they will be allowed to start more instances.  Low trust level accounts will be limited in whole by a function related to the global compute rate (similar to global hash rate for cryptocoin miners).  This function should provide a market price of anonymous server starts and work nicely with a system based on karma.

Hackers are encouraged to utilize the system for whatever purpose they deem important, but should consider the implications of their actions are being tied directly to the cost of starting instances for non-trusted entities.  Being naughty with this will cost you.

### Funding
The StackMonkey service, it's employees and it's investors expect to be rewarded accordingly for bringing this concept to fruition.  Discussion around ownership share is encouraged, but this author feels strongly about the concept of "Benevolent Dictatorship".  It is my intent to do what is right for the ecosystem first (which entails considering the effects of features on power pooling) and what is right for the shareholders of the corporation second.

A governance board will be established which in turn represents the interests of the corporation.  The corporation itself will be a multi-national corporation which will be eventually be controlled by an autonomous corporation implemented with Ethereum or similar.  This corporation will be open to public investment via Bitcoin and other currencies.

Initial investments by venture capital or institutions will be papered in a traditional way, but the shares issued to these entities will be based on shares of colored cryptcoins.

The implementation of this funding is TBD and assistance is needed for determining the best course for the project.

Donations for the project can be made at 1JT1mQS74Ub8jyxQ81aKEeoyudSRX8RJTA.  I have about 6 month's burn available to me for this project and will need assistance ASAP to accelerate it to fruition.  Your donations will be treated as an investment once the fund details are decided upon.

A git commit history of this document is provided at: https://gist.github.com/kordless/8461482

Kord Campbell
Coder and Evangelist
XOV.IO

