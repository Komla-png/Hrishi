# Google Cloud Organization Policy Workaround

Your organization has blocked service account key creation via policy: `iam.disableServiceAccountKeyCreation`

## 🔧 Required Permissions

Only users with the **"Organization Policy Administrator"** role can make changes. This role has permissions for:
- `orgpolicy.policy.get`
- `orgpolicy.policies.create`
- `orgpolicy.policies.delete`
- `orgpolicy.policies.update`

---

## 📋 For Your Organization Admin

### Quick Overview
You need to **temporarily disable** the service account key creation restriction to allow a one-time key creation for a Flask dashboard Google Sheets integration project.

### Step-by-Step Instructions for Admin

**1. Navigate to Organization Policies**
   - Go to: https://console.cloud.google.com
   - Search for "Organization Policies" in the search bar
   - Click on it

**2. Find the Policy**
   - In the "Policy details" search box, type: `iam.disableServiceAccountKeyCreation`
   - OR search for: `Disable service account key creation`
   - Click on it

**3. Check Current Status**
   - Look at the "Policy source" - it shows this is "Inherit parent's policy"
   - The status is currently ENFORCED

**4. Disable Temporarily**
   - Click the **"Manage policy"** button
   - Click **"DELETE ENFORCEMENT"** (or "DISABLE")
   - Confirm the action
   - **This takes effect immediately** (< 1 minute)

**5. Allow User to Create Key**
   - Give the user ~5 minutes to create the service account key
   - They will go to: Google Cloud Console → APIs & Services → Credentials
   - Click on "sheets-sync" service account → KEYS tab
   - Click "ADD KEY" → "Create new key" → JSON format → CREATE

**6. Re-Enable Policy (Optional)**
   - After user confirms the key is created
   - Go back to the same organization policy page
   - Click "Manage policy" again
   - Click "ENFORCE" to re-enable the restriction

### Reference Information
- **Policy ID:** `iam.disableServiceAccountKeyCreation` (or `iam.managed.disableServiceAccountKeyCreation`)
- **Project:** My Project 39840
- **Service Account:** sheets-sync@gold-freedom-489515-c6.iam.gserviceaccount.com
- **Purpose:** One-time JSON key creation for Flask dashboard Google Sheets sync
- **Tracking Number:** c661418487233635

---

### Step 2: Once Key Access is Approved

After your admin disables the policy (or creates the key for you):

1. **Go to Google Cloud Console:** https://console.cloud.google.com
2. **Navigate to:** APIs & Services → Credentials
3. **Find Service Account:** Look for "sheets-sync" in the "Service Accounts" section
4. **Click the email address** to open service account details
5. **Go to KEYS tab** at the top
6. **Click ADD KEY → Create new key**
7. **Choose JSON format**
8. **Click CREATE**
9. **Save the file** as: `instance/google_service_account.json`

---

### Step 3: Check for Existing Keys

Sometimes organizations pre-create keys. Try this:

1. In the KEYS tab, check if there's already a key listed
2. If yes, click the **pencil icon** to download it
3. Save it as `instance/google_service_account.json`

---

## ⏱️ Temporary Admin Access Request

If your organization doesn't want to permanently disable the policy, ask your admin to:
- **Temporarily disable** the policy
- **Create one service account key** for your project
- **Re-enable** the policy afterward

This takes about 5 minutes to do.

---

## 📋 What to Provide Your Admin

Send them this information:

```
Project: gold-freedom-489515
Service Account: sheets-sync@gold-freedom-489515-c6.iam.gserviceaccount.com
Required Format: JSON key file
Purpose: Google Sheets data sync for Flask dashboard
Blocked Policy: iam.disableServiceAccountKeyCreation
```

---

## Once You Have the Key...

Once your admin provides the key or the policy is temporarily disabled:

1. Save the JSON file as: `instance/google_service_account.json`
2. Run the setup validator:
   ```powershell
   python setup_google_sheets.py
   ```
3. Continue with the remaining setup steps

---

## Need Help?

- **Validation script:** `python setup_google_sheets.py`
- **Full setup guide:** `SETUP_STEPS.md`
- **Technical docs:** `GOOGLE_SHEETS_SYNC_SETUP.md`

Contact your Google Cloud admin and reference this document when requesting access!
