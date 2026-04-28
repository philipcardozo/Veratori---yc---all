# Fix: Folder Upload Error in cPanel

## The Problem
cPanel File Manager's upload feature **cannot upload folders directly**. It can only upload individual files. That's why you see:
- ✅ HTML files uploaded successfully
- ❌ Folders failed with "attempted to upload a folder" error

## Solution: Upload Folders via ZIP

### Step 1: Create a ZIP File on Your Mac

1. **Navigate to your out folder**:
   ```bash
   cd /Users/felipecardozo/Desktop/coding/Veratori/out
   ```

2. **Select all contents** (not the folder itself, but everything inside):
   - Open Finder
   - Go to `/Users/felipecardozo/Desktop/coding/Veratori/out`
   - Select ALL files and folders (Cmd+A)
   - Right-click → "Compress X Items"

3. **This creates a ZIP file** (probably called `Archive.zip` or similar)

### Step 2: Upload ZIP to cPanel

1. **In cPanel File Manager**, go to `public_html`
2. **Click "Upload"**
3. **Upload the ZIP file** you just created
4. **Wait for upload to complete**

### Step 3: Extract the ZIP

1. **Right-click the ZIP file** in File Manager
2. **Select "Extract"** or "Extract Archive"
3. **Wait for extraction** (this creates all the folders and files)
4. **Delete the ZIP file** after extraction is complete

### Step 4: Verify Structure

Your `public_html` should now contain:
- `_next/` folder (with all subfolders)
- `about/` folder
- `contact/` folder
- `mission/` folder
- `product/` folder
- `_not-found/` folder
- `index.html`
- `404.html`
- `_not-found.html`
- All other HTML files

## Alternative: Manual Folder Creation

If ZIP doesn't work, create folders manually:

1. **In File Manager**, click "New Folder" for each:
   - `_next`
   - `about`
   - `contact`
   - `mission`
   - `product`
   - `_not-found`

2. **Upload files into each folder**:
   - Open each folder
   - Upload the files that belong in that folder

3. **For the `_next` folder** (most important):
   - Create `_next` folder
   - Inside it, create `static` folder
   - Inside `static`, create `chunks` and `media` folders
   - Upload all the files to their respective locations

**Note**: This method is tedious. ZIP extraction is much easier!

## Best Solution: Use FTP

If you have FTP access, use an FTP client (FileZilla, Cyberduck, Transmit):

1. **Get FTP credentials** from cPanel → "FTP Accounts"
2. **Connect via FTP**
3. **Upload entire folder structure** - FTP supports folders natively
4. **Much faster and easier!**

---

**Quick Fix**: Just ZIP the `out` folder contents and extract in cPanel. That's the easiest solution!
