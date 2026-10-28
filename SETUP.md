# Servus German — setup (about 45 minutes, once)

Everything happens in your own browser. Passwords and payment details stay with you; the only key
(Buffer API key) goes into GitHub's encrypted secrets. Texts and images to paste are in the
**Setup kit** of the Servus German Studio page.

## A · Accounts (≈ 20 min)

1. **Email:** create one free Gmail for the brand. Use it for every sign-up below.
2. **TikTok:** sign up, username `servusgerman` (or the first free fallback from the kit).
   Settings → Account → *Switch to Business Account* (category *Education*).
   Profile: name *Servus German*, photo `kit/profile.png`, bio from the kit.
3. **Instagram:** sign up with the same username. Settings → *Account type and tools* → *Switch to professional account* → *Creator* (category *Education*). Profile as above.
4. **YouTube:** go to youtube.com with the Gmail → *Create a channel* → name *Servus German*, handle `@servusgerman`.
   Upload the banner and picture from the kit and paste the description.

## B · Buffer (≈ 10 min)

5. Sign up at **buffer.com** (free plan) with the Gmail. *Connect channels* → TikTok, Instagram, YouTube (each opens a login pop-up).
6. Open **publish.buffer.com/settings/api** → *Create API key* → copy it. Keep the tab open.

## C · GitHub (≈ 15 min)

7. **github.com** → sign up or log in → **New repository**: name `servus-german`, **Public**, no README → *Create repository*.
8. Unzip the four `servus-german-autopilot-*.zip` files. They all unpack into the same folder `servus-german`. Upload it:
   - **Terminal:**
     ```
     cd servus-german
     git init -b main && git add . && git commit -m "Servus German autopilot"
     git remote add origin https://github.com/<your-username>/servus-german.git
     git push -u origin main
     ```
   - **No terminal:** GitHub Desktop → *File → Add local repository* → pick the folder → *Publish repository* (untick *Keep this code private*).
9. Repo **Settings → Secrets and variables → Actions → New repository secret**: name `BUFFER_API_KEY`, value = the key from step 6.
10. Repo **Settings → Pages**: *Deploy from a branch* → `main` / `(root)` → *Save*.
11. **Actions** tab → enable workflows if asked → **Autopilot** → *Run workflow*.
    The first run sets day 1 to tomorrow and schedules the first 7 days in Buffer.
12. Open **https://&lt;your-username&gt;.github.io/servus-german/**: that's Mission Control. Bookmark it on your phone.
    Tell Claude your GitHub username so it can check the first run.

## D · Shop (≈ 15 min, can be later)

13. **payhip.com** → sign up (free plan) → *Settings → Payments*: connect PayPal or Stripe.
14. *Add product → Digital download*:
    - *The Austrian German Survival Guide*: upload the PDF, price €0, cover + description from the kit.
    - *Starter Deck*: upload `Servus-German-Starter-Deck.zip`, price €9, cover + description from the kit.
15. Copy your store link into the TikTok, Instagram and YouTube bios. Optional: paste it into `config.json` → `links.shop`
    (pencil icon on GitHub) so Mission Control links to it.

## E · Pinterest (optional)

16. Create a free Pinterest business account and a board *Learn German*.
17. Ask Claude for `pinterest/bulk-pins.csv` with your username, then Pinterest → *Create → Bulk create Pins* → upload it.

If anything is red on Mission Control, the message says what to fix. Most common: a platform logged Buffer out → reconnect it in Buffer.
