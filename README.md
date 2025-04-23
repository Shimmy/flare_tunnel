# Flare

A wrapper for Cloudflare Tunnels that works like ngrok, allowing you to easily expose local services to the internet with a single command.

## Installation

### Prerequisites

1. Install cloudflared:
   ```
   # Debian/Ubuntu
   curl -L https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-linux-amd64.deb -o cloudflared.deb
   sudo dpkg -i cloudflared.deb
   
   # macOS
   brew install cloudflared
   
   # Other platforms
   # See https://developers.cloudflare.com/cloudflare-one/connections/connect-apps/install-and-setup/installation
   ```

2. Install flare:
   ```
   pip install flare-tunnel
   ```

3. Set your Cloudflare API key as an environment variable:
   ```
   # Using API Token (recommended)
   export CLOUDFLARE_API_KEY=your_cloudflare_api_token
   
   # OR using Global API Key (legacy method)
   export CLOUDFLARE_API_KEY=your_email@example.com:your_global_api_key
   ```
   
   To get an API token (recommended):
   1. Go to Cloudflare dashboard → Profile → API Tokens
   2. Create a token with the following permissions:
      - Account.Cloudflare Tunnel:Edit
      - Account.Cloudflare Tunnel:Read
      - Zone.Zone:Read
   
   The script will automatically detect which authentication method you're using.

## Usage

```
flare [TUNNEL_NAME] PORT [DOMAIN] [--local-addr LOCAL_ADDRESS] [--no-timestamp] [--debug]
```

Examples:
```
# Auto-generated tunnel name
flare 3000

# Specify a tunnel name (with auto-timestamp)
flare myapp 3000

# Use a specific name without timestamp
flare myapp 3000 --no-timestamp

# Custom domain (must be in your Cloudflare account)
flare myapp 3000 example.com

# With a different local address (e.g., 0.0.0.0)
flare myapp 3000 --local-addr 0.0.0.0

# With debug mode enabled (for troubleshooting)
flare myapp 3000 --debug
```

The script will:
1. Use a domain from your Cloudflare account if available, or fallback to Cloudflare's auto-generated domain (like trycloudflare.com)
2. Add a timestamp to the tunnel name for uniqueness (unless you use --no-timestamp)
3. Auto-generate a random name if you only specify a port
4. Clean up all resources (tunnel and DNS records) when stopping

Use the `--debug` flag to enable additional debugging information if you run into problems.

## Features

- Simple, ngrok-like interface
- No OAuth flow or browser-based authentication needed
- Just uses API key via environment variable
- Support for auto-generated random tunnel names
- Optional control over tunnel naming (with or without timestamps)
- Support for custom domains from your Cloudflare account
- Uses Cloudflare's auto-generated domains when no domain is available
- Support for custom local addresses (localhost, 127.0.0.1, 0.0.0.0, etc.)
- Thorough cleanup of tunnels and DNS records when the script exits
- Clean, user-friendly output

## Requirements

- Python 3.6+
- `requests` library (installed automatically)
- `cloudflared` CLI installed
- Cloudflare account with API token