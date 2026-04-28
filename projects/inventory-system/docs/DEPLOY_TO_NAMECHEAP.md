# Deploy Veratori to Namecheap - Step-by-Step Guide

This guide will walk you through deploying your Next.js website to Namecheap shared hosting.

## Prerequisites

- Node.js installed on your local machine
- Namecheap hosting account with cPanel access
- FTP credentials or cPanel File Manager access

## Step 1: Build Your Website Locally

1. **Open Terminal** and navigate to your project directory:
   ```bash
   cd /Users/felipecardozo/Desktop/coding/Veratori
   ```

2. **Install dependencies** (if not already done):
   ```bash
   npm install
   ```

3. **Build the static website**:
   ```bash
   npm run build
   ```

   This will create a folder called `out` in your project directory containing all the static files ready for upload.

## Step 2: Prepare Files for Upload

After building, you'll have an `out` folder. This contains all the files you need to upload to Namecheap.

**Important**: You need to upload the **contents** of the `out` folder (not the folder itself) to your `public_html` directory.

## Step 3: Upload to Namecheap via cPanel File Manager

1. **Log into cPanel**:
   - Go to your Namecheap account
   - Click on "Manage" next to your hosting account
   - Click "cPanel" or access it directly

2. **Open File Manager**:
   - In cPanel, find and click on "File Manager"
   - Navigate to `public_html` folder (this is your website's root directory)

3. **Clear existing files** (if any):
   - Select all files in `public_html` (if the directory is not empty)
   - Click "Delete" to remove them
   - Confirm deletion

4. **Upload your website files**:
   - Click the "Upload" button in the File Manager toolbar
   - Navigate to your local `out` folder on your computer
   - **Select ALL files and folders** inside the `out` directory:
     - `_next/` folder
     - `about/` folder
     - `contact/` folder
     - `mission/` folder
     - `product/` folder
     - `index.html`
     - Any other files/folders
   - Click "Upload" and wait for all files to upload

   **Alternative Method - Using ZIP**:
   - On your local machine, zip the entire contents of the `out` folder
   - Upload the ZIP file to `public_html`
   - In File Manager, right-click the ZIP file and select "Extract"
   - Delete the ZIP file after extraction

## Step 4: Verify Upload

1. **Check file structure**:
   - In File Manager, verify that `public_html` contains:
     - `index.html`
     - `_next/` folder
     - `about/`, `contact/`, `mission/`, `product/` folders

2. **Set correct permissions** (if needed):
   - Folders should have permission `755`
   - Files should have permission `644`
   - You can set these by right-clicking files/folders → "Change Permissions"

## Step 5: Test Your Website

1. **Visit your domain**:
   - Open your browser and go to `https://yourdomain.com`
   - Replace `yourdomain.com` with your actual domain name

2. **Test all pages**:
   - Homepage: `https://yourdomain.com`
   - About: `https://yourdomain.com/about`
   - Contact: `https://yourdomain.com/contact`
   - Mission: `https://yourdomain.com/mission`
   - Product: `https://yourdomain.com/product`

3. **Check for issues**:
   - Verify images load correctly
   - Check that navigation works
   - Test responsive design on mobile

## Troubleshooting

### Images not loading
- Ensure the `_next` folder was uploaded correctly
- Check that image paths are correct in the browser console

### 404 errors on pages
- Make sure all folders (about, contact, mission, product) were uploaded
- Verify each folder contains an `index.html` file

### CSS/styles not working
- Check that the `_next/static` folder was uploaded
- Clear your browser cache (Ctrl+Shift+R or Cmd+Shift+R)

### Website shows "Index of /" page
- Make sure `index.html` is in the `public_html` root directory
- Verify file permissions are set correctly

## Alternative: Using FTP

If you prefer using FTP software (like FileZilla, Cyberduck, or Transmit):

1. **Get FTP credentials** from Namecheap cPanel:
   - Go to cPanel → "FTP Accounts"
   - Note your FTP host, username, and password

2. **Connect via FTP**:
   - Host: `ftp.yourdomain.com` or the IP provided
   - Username: Your FTP username
   - Password: Your FTP password
   - Port: 21

3. **Upload files**:
   - Navigate to `/public_html/` on the server
   - Upload all contents from your local `out` folder
   - Maintain the folder structure

## Updating Your Website

Whenever you make changes:

1. Make your code changes locally
2. Run `npm run build` again
3. Upload the new contents of the `out` folder to `public_html` (replace old files)
4. Clear browser cache and test

## Need Help?

- **Namecheap Support**: https://www.namecheap.com/support/
- **cPanel Documentation**: https://docs.cpanel.net/

---

**Quick Command Reference**:
```bash
# Build the website
npm run build

# The output will be in the 'out' folder
# Upload everything inside 'out' to public_html
```
