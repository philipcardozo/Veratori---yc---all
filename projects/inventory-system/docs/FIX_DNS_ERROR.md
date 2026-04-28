# Fix DNS Error: "DNS_PROBE_FINISHED_NXDOMAIN"

## The Problem
Your files are uploaded correctly to `public_html`, but the domain `veratori.com` isn't resolving. This is a **DNS configuration issue**, not a file upload problem.

## Solution Steps

### Step 1: Verify Domain is Added in cPanel

1. **Log into cPanel**
2. **Look for "Addon Domains" or "Subdomains"** in the main cPanel dashboard
3. **Check if `veratori.com` is listed**:
   - If **NOT listed**: You need to add it (see Step 2)
   - If **listed**: Check DNS settings (see Step 3)

### Step 2: Add Domain to cPanel (If Not Added)

1. In cPanel, find **"Addon Domains"** or **"Parked Domains"**
2. Click on it
3. **Add `veratori.com`**:
   - **New Domain Name**: `veratori.com`
   - **Subdomain**: Usually auto-filled (like `veratori`)
   - **Document Root**: Should be `/public_html` or `/public_html/veratori.com`
   - Click **"Add Domain"**

### Step 3: Configure DNS in Namecheap

The domain needs to point to Namecheap's hosting servers:

1. **Go to Namecheap Domain List**:
   - Log into Namecheap account
   - Go to **"Domain List"**
   - Find `veratori.com`
   - Click **"Manage"**

2. **Check Nameservers**:
   - Go to **"Nameservers"** section
   - Should be set to **"Namecheap BasicDNS"** or **"Custom DNS"**
   - If using Custom DNS, you need Namecheap's nameservers (usually something like):
     - `dns1.registrar-servers.com`
     - `dns2.registrar-servers.com`
   - **OR** if you have a hosting account, use the hosting nameservers (check your hosting welcome email)

3. **Set A Record** (if using Custom DNS):
   - Go to **"Advanced DNS"** tab
   - Add/Edit **A Record**:
     - **Host**: `@` (or leave blank)
     - **Value**: Your hosting server IP (get this from Namecheap hosting panel)
     - **TTL**: Automatic or 300
   - Add **CNAME Record** for `www`:
     - **Host**: `www`
     - **Value**: `veratori.com` (or `@`)
     - **TTL**: Automatic or 300

### Step 4: Get Your Hosting Server IP

1. In Namecheap hosting panel, go to **"Manage"** for your hosting account
2. Look for **"Server Information"** or **"Account Information"**
3. Note the **Shared IP Address** or **Dedicated IP**
4. Use this IP in your DNS A record

### Step 5: Wait for DNS Propagation

After making DNS changes:
- **Wait 24-48 hours** for DNS to propagate globally
- You can check propagation status at: https://www.whatsmydns.net/
- Some changes can take effect in minutes, others take hours

### Step 6: Test with Temporary URL

While waiting for DNS, you can test your site using Namecheap's temporary URL:

1. In cPanel, look for **"Server Information"** or check your hosting welcome email
2. You'll see a temporary URL like: `http://your-server-ip/~username/` or `http://your-account-name.server-name.com/`
3. Visit this URL to verify your site works (files are correct)

## Quick Checklist

- [ ] Domain added in cPanel as Addon/Parked domain
- [ ] Nameservers configured in Namecheap
- [ ] A Record points to hosting server IP
- [ ] CNAME for www subdomain
- [ ] Waited for DNS propagation (24-48 hours)
- [ ] Tested with temporary URL

## Common Issues

### "Domain not found in cPanel"
- Add it as an Addon Domain in cPanel
- Make sure Document Root is set to `public_html`

### "Nameservers not configured"
- In Namecheap, set nameservers to Namecheap's or your hosting provider's
- Check your hosting welcome email for correct nameservers

### "DNS still not working after 48 hours"
- Double-check A Record IP address is correct
- Verify nameservers are correct
- Contact Namecheap support for assistance

## Need Help?

- **Namecheap Support**: https://www.namecheap.com/support/
- **DNS Check Tool**: https://www.whatsmydns.net/
- **cPanel Documentation**: https://docs.cpanel.net/

---

**Important**: Your files are uploaded correctly! This is purely a DNS/domain configuration issue. Once DNS is configured properly, your site will work.
