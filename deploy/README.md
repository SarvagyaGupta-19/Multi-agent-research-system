# Deployment Guide

Step-by-step instructions to deploy the Multi-Agent Research System to production.

- **Backend:** AWS EC2 (Ubuntu 22.04, t2.micro)
- **Frontend:** Vercel (free tier)

---

## Part A — Backend (AWS EC2)

### Step 1: Launch an EC2 Instance

1. Go to [AWS EC2 Console](https://console.aws.amazon.com/ec2/)
2. Click **Launch Instance**
3. Configure:
   - **Name:** `multi-agent-research`
   - **AMI:** Ubuntu Server 22.04 LTS (free tier eligible)
   - **Instance type:** `t2.micro` (free tier) or `t3.small`
   - **Key pair:** Create a new one or select existing (you'll need this to SSH)
   - **Security Group:** Create with these inbound rules:
     | Type  | Port | Source    | Purpose          |
     |-------|------|-----------|------------------|
     | SSH   | 22   | My IP     | SSH access       |
     | HTTP  | 80   | 0.0.0.0/0 | API (via Nginx) |
     | HTTPS | 443  | 0.0.0.0/0 | Future SSL       |
4. Click **Launch Instance**
5. Note the **Public IPv4 address** from the instance details

### Step 2: SSH into the Instance

```bash
# Replace with your key file and EC2 public IP
ssh -i "your-key.pem" ubuntu@<EC2_PUBLIC_IP>
```

### Step 3: Run the Setup Script

```bash
# Clone the repo and run setup
git clone https://github.com/SarvagyaGupta-19/Multi-agent-research-system.git ~/multi-agent-research
cd ~/multi-agent-research
sudo bash deploy/setup.sh
```

### Step 4: Configure API Keys

```bash
nano ~/multi-agent-research/.env
```

Add your keys:
```
GROQ_API_KEY=gsk_your_key_here
TAVILY_API_KEY=tvly-dev-your_key_here
MEM0_API_KEY=m0-your_key_here
ALLOWED_ORIGINS=https://your-app.vercel.app,http://localhost:3000
```

Then restart the service:
```bash
sudo systemctl restart research-api
```

### Step 5: Verify

```bash
# Check service is running
sudo systemctl status research-api

# Test health endpoint
curl http://localhost/health
# Expected: {"status":"ok","version":"0.3.0"}

# Test from your local machine (replace IP)
curl http://<EC2_PUBLIC_IP>/health
```

### Useful Commands

```bash
sudo systemctl status research-api     # Check status
sudo systemctl restart research-api    # Restart
sudo journalctl -u research-api -f     # Stream logs
sudo journalctl -u research-api -n 50  # Last 50 log lines
sudo systemctl status nginx            # Check Nginx
sudo nginx -t                          # Test Nginx config
```

---

## Part B — Frontend (Vercel)

### Step 1: Install Vercel CLI (optional, can use dashboard instead)

```bash
npm i -g vercel
```

### Step 2: Deploy via Vercel Dashboard (recommended)

1. Go to [vercel.com](https://vercel.com/) and sign in with GitHub
2. Click **Add New → Project**
3. Import your `Multi-agent-research-system` repo
4. Configure:
   - **Root Directory:** `frontend`
   - **Framework Preset:** Next.js (auto-detected)
5. Add **Environment Variable:**
   - Key: `NEXT_PUBLIC_API_URL`
   - Value: `http://<EC2_PUBLIC_IP>` (your EC2 public IP)
6. Click **Deploy**

### Step 3: Update CORS on EC2

Once Vercel gives you a URL (e.g., `https://multi-agent-research.vercel.app`), update the EC2 `.env`:

```bash
ssh -i "your-key.pem" ubuntu@<EC2_PUBLIC_IP>
nano ~/multi-agent-research/.env

# Update ALLOWED_ORIGINS to include your Vercel URL:
# ALLOWED_ORIGINS=https://multi-agent-research.vercel.app,http://localhost:3000

sudo systemctl restart research-api
```

### Step 4: End-to-End Test

1. Open your Vercel URL in the browser
2. Enter a research topic (e.g., "quantum computing applications 2025")
3. Select a style and click "Begin Analysis"
4. Wait for the pipeline to complete
5. Verify you see the report, trust score, and claims

---

## Troubleshooting

### Backend won't start
```bash
# Check logs for errors
sudo journalctl -u research-api -n 100
# Common issue: missing .env keys
```

### CORS errors in browser
```bash
# Make sure ALLOWED_ORIGINS in .env includes your Vercel URL
# Restart after changes:
sudo systemctl restart research-api
```

### 429 Too Many Requests
The Nginx rate limiter is set to 10 req/s with a burst of 20. If you hit this during normal use, increase the limit in `/etc/nginx/sites-available/research-api`.

### EC2 runs out of memory (t2.micro = 1GB RAM)
```bash
# Add swap space
sudo fallocate -l 1G /swapfile
sudo chmod 600 /swapfile
sudo mkswap /swapfile
sudo swapon /swapfile
echo '/swapfile none swap sw 0 0' | sudo tee -a /etc/fstab
```
