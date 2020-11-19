# VMC Lab Portal

## Overview
The Lab Portal is a self-service web application designed to enable public internet access to your VM workloads.  **The Lab Portal is an internal app and must be accessed from within the VMC lab.**

## Getting Started
### Simple Tutorial
The following a simple example of using the portal to create the necessary resources within VMC to allow public internet access to your VM or load balancer virtual server.
1. Access the lab VDI using a browser or the Horizon desktop client
2. Open Chrome and browse to https://portal.vmwarepso.org
3. Login with your domain admin account
4. Request a public IP
    1. Click **Public IPs** from the vertical nav
    2. Click **REQUEST PUBLIC IP**
    3. Enter a friendly name for your IP (e.g., UE-JSmith-UAG)
    4. Click **SUBMIT**
    5. A green alert message will be displayed once the IP is request is successful
    6. Copy the public IP that was provisioned for you
        1. If you don't see the IP, refresh the page or sort the table by name
5. Create a DNS record for your newly provisioned public IP address
    1. Click **Public DNS** from the vertical nav
    2. Click **ADD DNS RECORD**
    3. Select a domain zone from the drop-down menu (e.g., euclab.net)
    4. Select the type of DNS record to create (e.g., A)
    5. Enter the domain name for the record
        1. The domain name will come before the zone you select
        2. Example: a domain name of jsmith-uag will create a DNS record of jsmith-uag.euclab.net
    6. Paste in the public IP in the Record Answer(s) test field
    7. Click **SUBMIT**
6. Create a NAT rule to map your public IP to an internal lab IP
    1. Click **NAT Rules**
    2. Click **ADD NAT RULE**
    3. Enter a friendly name for the rule (e.g., UE-JSmith-UAG)
    4. Paste in the public IP in the Public IP text field
    5. Enter in the internal IP that the public IP should map to
        1. The public IP can map to any available IP on any network segment
        2. Any network segment can be used but the **U-DMZ-External (10.100.68.0/24)** network is recommended for user environment (UE) workloads that are public internet facing.  This IP could be the IP of your VM on the U-DMZ-External network or the IP of a load balancer virtual server (i.e., a virtual IP or VIP).
        3. Ensure to reserve this IP from the U-DMZ-External IP Addressing Confluence page and check that no servers are using the IP to avoid an IP conflict.
    6. Leave the Enable Rule switch set to **on**
    7. Click **SUBMIT**
8. Optionally review the Compute Gateway (CGW) Firewall Rules to ensure your workload specific traffic is allowed.
    1. CGW rules can be created and modified by lab admins only
    2. The following application services are allowed to all network segments:
        1. Kerberos (UDP 88) 
        2. HTTP (TCP port 80)
        3. HTTPS (TCP port 443)
        4. TCP ports 2001, 2020, 4172, 8443, 9543, and 10443
9. Optionally download a wildcard web certificate for your app server
    1. Click **Certificates**
    2. Click **DOWNLOAD** for the certificate specific to the DNS zone you created earlier (e.g., *.euclab.net)
    3. Unzip the downloaded file
    4. Install the PEM or PFX version of the cert on your app server or associate the load balancer virtual server with this cert if doing SSL/TLS inspection or re-encryption

## Integrations
1. NS1 for DNS management
2. NSX VMC AWS Integration API for public IP management
3. NSX VMC Policy API for all other management aspects
4. LDAP integration with Windows Active Directory for domain user account login and session management

## Technologies Used
The web app frontend was built using [Clarity Design System](https://next.clarity.design/) and [Angular](https://angular.io/).
The backend is a REST API app built using Python 3 and Flask.
Both the frontend and backend are hosted on a Windows Server 2019 VM running IIS.

## Setup and Deployment
Please see SETUP.md for guidance on setting up your server to host the web app, deploying for production use, and development setup.