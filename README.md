﻿# boomi-migration

# [Bhoomi](https://boomi.com/)
```
- we need a credentials of bhoomi account for the login
- then we need to create in IS to run the account id

Logic :
	1. we have package  "Boomi Assesment Tool API Flows"
	2. we will get accountid and username from the customers  
	3. iflow will log-in to the boomi account
	4. we can create a username and password in `Security Material> BoomiUser`
	5. Proxy is `BoomiAssess` check if it is there, when facing issue check the package and proxy
the data is converted to csv format in the iflow
	6. `Extract Metadata` and `Evaluate Metadata` are the flows we need to check when facing problem 

```

## Migration tool using this bhoomi integration

```
- dummy iflow creation
- palette option are drag an drop we 
```
## Deployment
Deployed app in render [https://boomi-migration.onrender.com](https://boomi-migration.onrender.com)
