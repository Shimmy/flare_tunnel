#!/usr/bin/env python3
import os
import sys
import json
import subprocess
import requests
import time
import signal
import atexit
import re
import random
import string
import argparse

CLOUDFLARE_API_URL = "https://api.cloudflare.com/client/v4"

def get_api_key():
    api_key = os.environ.get("CLOUDFLARE_API_KEY")
    if not api_key:
        print("Error: CLOUDFLARE_API_KEY environment variable not set")
        sys.exit(1)
    return api_key

def get_headers():
    api_key = get_api_key()
    
    # If API key starts with a domain or email, it's likely an API token that doesn't need Bearer
    # If it's a shorter alphanumeric token, it's likely a scoped API token that needs Bearer
    if '@' in api_key or '.' in api_key:
        # This is likely an email:key format (Global API Key)
        email, key = api_key.split(':')
        return {
            "X-Auth-Email": email,
            "X-Auth-Key": key,
            "Content-Type": "application/json"
        }
    else:
        # This is likely an API Token
        return {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json"
        }

def get_account_id():
    headers = get_headers()
    response = requests.get(f"{CLOUDFLARE_API_URL}/accounts", headers=headers)
    
    if response.status_code != 200:
        print(f"Error getting account ID: {response.status_code}")
        try:
            print(response.json())
        except json.JSONDecodeError:
            print(f"Response content: {response.content}")
        sys.exit(1)
    
    accounts = response.json().get("result", [])
    if not accounts:
        print("No Cloudflare accounts found")
        sys.exit(1)
    
    return accounts[0]['id']

def create_tunnel(account_id, tunnel_name, debug=False):
    headers = get_headers()
    
    # Check if tunnel with this name already exists
    if debug:
        print(f"Debug: Checking for existing tunnel named '{tunnel_name}'")
        print(f"Debug: API URL: {CLOUDFLARE_API_URL}/accounts/{account_id}/tunnels")
        print(f"Debug: Headers: {headers}")
    
    response = requests.get(
        f"{CLOUDFLARE_API_URL}/accounts/{account_id}/tunnels",
        headers=headers
    )
    
    if debug:
        print(f"Debug: List tunnels response status: {response.status_code}")
        print(f"Debug: Response headers: {response.headers}")
        print(f"Debug: Response content: {response.content[:200]}")
    
    if response.status_code != 200:
        print(f"Error checking existing tunnels: {response.status_code}")
        try:
            print(response.json())
        except json.JSONDecodeError:
            print(f"Response content: {response.content}")
        sys.exit(1)
    
    tunnels = response.json().get("result", [])
    for tunnel in tunnels:
        if tunnel.get("name") == tunnel_name:
            if debug:
                print(f"Debug: Found existing tunnel with ID: {tunnel['id']}")
            return tunnel["id"], tunnel["name"]
    
    # Create a new tunnel
    data = {
        "name": tunnel_name,
        "tunnel_secret": ''.join(random.choices(string.ascii_letters + string.digits, k=32))
    }
    
    if debug:
        print(f"Debug: Creating new tunnel with name: {tunnel_name}")
        print(f"Debug: API URL: {CLOUDFLARE_API_URL}/accounts/{account_id}/tunnels")
        # Don't print the secret in logs
        print(f"Debug: Request data: {json.dumps({k: v if k != 'tunnel_secret' else '[SECRET]' for k, v in data.items()})}")
    
    response = requests.post(
        f"{CLOUDFLARE_API_URL}/accounts/{account_id}/tunnels",
        headers=headers,
        json=data
    )
    
    if debug:
        print(f"Debug: Create tunnel response status: {response.status_code}")
        print(f"Debug: Response headers: {response.headers}")
        print(f"Debug: Response content: {response.content[:200]}")
    
    if response.status_code != 200:
        print(f"Error creating tunnel: {response.status_code}")
        try:
            print(response.json())
        except json.JSONDecodeError:
            print(f"Response content: {response.content}")
        sys.exit(1)
    
    result = response.json().get("result", {})
    tunnel_id = result.get("id")
    tunnel_name = result.get("name")
    
    if debug:
        print(f"Debug: Created tunnel with ID: {tunnel_id}, Name: {tunnel_name}")
    
    if not tunnel_id:
        print("Error: Failed to get tunnel ID from response")
        print(f"Response content: {response.content}")
        sys.exit(1)
        
    return tunnel_id, tunnel_name

def create_tunnel_with_credentials(account_id, tunnel_name, debug=False):
    headers = get_headers()
    
    if debug:
        print(f"Debug: Creating a fresh tunnel with credentials for {tunnel_name}")
    
    # Generate random tunnel secret
    tunnel_secret = os.urandom(32).hex()
    
    if debug:
        print(f"Debug: Generated tunnel secret (not shown for security)")
    
    # Create the tunnel using the newer cfd_tunnel endpoint
    data = {
        "name": tunnel_name,
        "tunnel_secret": tunnel_secret
    }
    
    if debug:
        print(f"Debug: Creating tunnel with API")
        print(f"Debug: POST {CLOUDFLARE_API_URL}/accounts/{account_id}/cfd_tunnel")
    
    response = requests.post(
        f"{CLOUDFLARE_API_URL}/accounts/{account_id}/cfd_tunnel",
        headers=headers,
        json=data
    )
    
    if debug:
        print(f"Debug: Tunnel creation response status: {response.status_code}")
        if response.status_code == 200:
            try:
                print(f"Debug: Response preview: {json.dumps(response.json())[:200]}")
            except:
                print(f"Debug: Non-JSON response: {response.content[:200]}")
    
    if response.status_code != 200:
        print(f"Error creating tunnel: {response.status_code}")
        try:
            print(response.json())
        except json.JSONDecodeError:
            print(f"Response content: {response.content}")
        sys.exit(1)
    
    # Get the tunnel ID
    result = response.json().get("result", {})
    tunnel_id = result.get("id")
    
    if not tunnel_id:
        print("Error: Failed to get tunnel ID from response")
        print(f"Response: {response.json()}")
        sys.exit(1)
    
    if debug:
        print(f"Debug: Created tunnel with ID: {tunnel_id}")
    
    # Now get the token for the tunnel
    token_response = requests.get(
        f"{CLOUDFLARE_API_URL}/accounts/{account_id}/cfd_tunnel/{tunnel_id}/token",
        headers=headers
    )
    
    if debug:
        print(f"Debug: Token retrieval response status: {token_response.status_code}")
        try:
            print(f"Debug: Token response preview: {json.dumps(token_response.json())[:200]}")
        except:
            print(f"Debug: Non-JSON token response: {token_response.content[:200]}")
    
    if token_response.status_code != 200:
        print(f"Error getting tunnel token: {token_response.status_code}")
        try:
            print(token_response.json())
        except json.JSONDecodeError:
            print(f"Response content: {token_response.content}")
        sys.exit(1)
    
    tunnel_token = token_response.json().get("result")
    
    if not tunnel_token:
        print("Error: Failed to get tunnel token from response")
        print(f"Response: {token_response.json()}")
        sys.exit(1)
    
    # Save the tunnel token directly
    token_file = f"/tmp/cloudflared_token_{tunnel_id}.txt"
    with open(token_file, "w") as f:
        f.write(tunnel_token)
    
    if debug:
        print(f"Debug: Saved token to {token_file}")
        print(f"Debug: Token content: {tunnel_token[:30]}...")
    
    return tunnel_id, token_file

def create_tunnel_config(account_id, tunnel_id, tunnel_name, port, local_addr="localhost", custom_domain=None, debug=False):
    domain = get_account_domain(account_id, debug)
    hostname = f"{tunnel_name}.{domain}"
    
    if debug:
        print(f"Debug: Creating tunnel configuration for tunnel ID: {tunnel_id}")
        print(f"Debug: Using hostname: {hostname}")
    
    # Configure the tunnel using the API
    headers = get_headers()
    config_data = {
        "config": {
            "ingress": [
                {
                    "hostname": hostname,
                    "service": f"http://{local_addr}:{port}"
                },
                {
                    "service": "http_status:404"
                }
            ]
        }
    }
    
    if debug:
        print(f"Debug: Configuring tunnel with API")
        print(f"Debug: PUT {CLOUDFLARE_API_URL}/accounts/{account_id}/cfd_tunnel/{tunnel_id}/configurations")
        print(f"Debug: Configuration: {json.dumps(config_data)}")
    
    response = requests.put(
        f"{CLOUDFLARE_API_URL}/accounts/{account_id}/cfd_tunnel/{tunnel_id}/configurations",
        headers=headers,
        json=config_data
    )
    
    if debug:
        print(f"Debug: Configuration response status: {response.status_code}")
        try:
            print(f"Debug: Response: {json.dumps(response.json())[:200]}")
        except:
            print(f"Debug: Could not parse response as JSON: {response.content[:200]}")
    
    # Try to set up DNS for the tunnel
    zone_id = "a2dbaff918c783a734197864e6cb7190"  # Using the zone ID from the bash script
    try:
        # Create CNAME DNS record
        dns_data = {
            "type": "CNAME",
            "name": tunnel_name,  # Use the full tunnel name with timestamp
            "content": f"{tunnel_id}.cfargotunnel.com",
            "ttl": 1,  # Auto
            "proxied": True
        }
        
        if debug:
            print(f"Debug: Creating DNS record")
            print(f"Debug: Using zone ID: {zone_id}")
        
        dns_response = requests.post(
            f"{CLOUDFLARE_API_URL}/zones/{zone_id}/dns_records",
            headers=headers,
            json=dns_data
        )
        
        if debug:
            print(f"Debug: DNS creation response status: {dns_response.status_code}")
            try:
                response_json = dns_response.json()
                print(f"Debug: DNS creation response: {json.dumps(response_json)[:200]}")
                
                # Check for error code 81057 (record exists)
                if not response_json.get("success"):
                    errors = response_json.get("errors", [])
                    if errors and errors[0].get("code") in [81057, 81053]:
                        print(f"Debug: DNS record already exists (this is OK)")
            except:
                print(f"Debug: Could not parse DNS response as JSON")
    except Exception as e:
        if debug:
            print(f"Debug: Failed to set up DNS: {str(e)}")
            print(f"Debug: This is not critical, continuing")
    
    return hostname, None  # We don't need a config file anymore

def get_account_domain(account_id, debug=False):
    """Get a domain from the Cloudflare account or use a default."""
    headers = get_headers()
    
    if debug:
        print(f"Debug: Getting domain for account: {account_id}")
    
    # First check for zones (domains) in the account
    response = requests.get(
        f"{CLOUDFLARE_API_URL}/accounts/{account_id}/zones",
        headers=headers
    )
    
    if debug:
        print(f"Debug: Zones response status: {response.status_code}")
    
    # Default domain in case we can't find one
    domain = "trycloudflare.com"
    
    try:
        if response.status_code == 200:
            result = response.json()
            zones = result.get("result", [])
            if zones:
                # Use the first zone/domain in the account
                domain = zones[0]["name"]
                if debug:
                    print(f"Debug: Found domain from account: {domain}")
                return domain
            elif debug:
                print(f"Debug: No zones found in account, using default domain: {domain}")
    except Exception as e:
        if debug:
            print(f"Debug: Error getting zones: {str(e)}")
            print(f"Debug: Using default domain: {domain}")
    
    return domain

def delete_tunnel_and_dns(account_id, tunnel_id, tunnel_name, zone_id=None, debug=False):
    """Delete the tunnel and its DNS records across all zones"""
    headers = get_headers()
    
    # 1. Get all zones in the account to ensure we check everywhere for the DNS record
    try:
        if debug:
            print(f"Debug: Getting list of zones for account {account_id}")
        
        zones_response = requests.get(
            f"{CLOUDFLARE_API_URL}/accounts/{account_id}/zones",
            headers=headers
        )
        
        all_zones = []
        if zones_response.status_code == 200:
            zones_data = zones_response.json()
            all_zones = zones_data.get("result", [])
            if debug:
                print(f"Debug: Found {len(all_zones)} zones in account")
        else:
            # If we can't get all zones but have a specified zone_id, use that
            if zone_id:
                all_zones = [{"id": zone_id, "name": "unknown"}]
                if debug:
                    print(f"Debug: Using provided zone_id: {zone_id}")
    except Exception as e:
        if debug:
            print(f"Debug: Error getting zones: {str(e)}")
        # Use the provided zone_id as fallback
        if zone_id:
            all_zones = [{"id": zone_id, "name": "unknown"}]
    
    # If we still don't have any zones and have a hardcoded ID, use it
    if not all_zones and zone_id:
        all_zones = [{"id": zone_id, "name": "unknown"}]
    
    # 2. Look for DNS records in all zones
    dns_records_deleted = 0
    
    for zone in all_zones:
        current_zone_id = zone["id"]
        zone_name = zone.get("name", "unknown")
        
        try:
            if debug:
                print(f"Debug: Checking for DNS records in zone {zone_name} ({current_zone_id})")
            
            # First try an exact match with the tunnel name
            dns_list_response = requests.get(
                f"{CLOUDFLARE_API_URL}/zones/{current_zone_id}/dns_records?name={tunnel_name}",
                headers=headers
            )
            
            if dns_list_response.status_code == 200:
                dns_records = dns_list_response.json().get("result", [])
                if dns_records:
                    for record in dns_records:
                        dns_id = record["id"]
                        record_name = record.get("name", "unknown")
                        
                        if debug:
                            print(f"Debug: Found DNS record '{record_name}' with ID: {dns_id}")
                        
                        # Delete the DNS record
                        delete_dns_response = requests.delete(
                            f"{CLOUDFLARE_API_URL}/zones/{current_zone_id}/dns_records/{dns_id}",
                            headers=headers
                        )
                        
                        if delete_dns_response.status_code == 200:
                            dns_records_deleted += 1
                            if debug:
                                print(f"Debug: Successfully deleted DNS record '{record_name}'")
                        elif debug:
                            print(f"Debug: Failed to delete DNS record '{record_name}': {delete_dns_response.status_code}")
            
            # Also try to find records that might include this tunnel name (with domain suffixes)
            # For example, if tunnel_name is "myapp-12345", search for "myapp-12345.example.com"
            if "." not in tunnel_name:  # Only if tunnel_name itself is not a full domain
                dns_list_response = requests.get(
                    f"{CLOUDFLARE_API_URL}/zones/{current_zone_id}/dns_records",
                    headers=headers
                )
                
                if dns_list_response.status_code == 200:
                    all_dns_records = dns_list_response.json().get("result", [])
                    for record in all_dns_records:
                        record_name = record.get("name", "")
                        # Check if this record begins with our tunnel name
                        if record_name.startswith(f"{tunnel_name}.") or record_name == tunnel_name:
                            dns_id = record["id"]
                            
                            if debug:
                                print(f"Debug: Found additional DNS record '{record_name}' with ID: {dns_id}")
                            
                            # Delete the DNS record
                            delete_dns_response = requests.delete(
                                f"{CLOUDFLARE_API_URL}/zones/{current_zone_id}/dns_records/{dns_id}",
                                headers=headers
                            )
                            
                            if delete_dns_response.status_code == 200:
                                dns_records_deleted += 1
                                if debug:
                                    print(f"Debug: Successfully deleted DNS record '{record_name}'")
                            elif debug:
                                print(f"Debug: Failed to delete DNS record '{record_name}': {delete_dns_response.status_code}")
        except Exception as e:
            if debug:
                print(f"Debug: Error checking/deleting DNS records in zone {zone_name}: {str(e)}")
    
    if debug:
        print(f"Debug: Total DNS records deleted: {dns_records_deleted}")
    
    # 3. Delete the tunnel
    tunnel_deleted = False
    try:
        if debug:
            print(f"Debug: Attempting to delete tunnel {tunnel_id}")
        
        delete_tunnel_response = requests.delete(
            f"{CLOUDFLARE_API_URL}/accounts/{account_id}/cfd_tunnel/{tunnel_id}",
            headers=headers
        )
        
        if delete_tunnel_response.status_code == 200:
            tunnel_deleted = True
            if debug:
                print(f"Debug: Successfully deleted tunnel {tunnel_id}")
        elif debug:
            print(f"Debug: Tunnel delete response: {delete_tunnel_response.status_code}")
    except Exception as e:
        if debug:
            print(f"Debug: Error deleting tunnel: {str(e)}")
    
    # Return the number of deleted DNS records
    return dns_records_deleted

def run_cloudflared(token_file, config_file, tunnel_id, account_id, tunnel_name, debug=False):
    if debug:
        print(f"Debug: Running cloudflared with token file: {token_file}")
    
    # Read token from file
    with open(token_file, "r") as f:
        token = f.read().strip()
    
    if debug:
        print(f"Debug: Read token from file, length: {len(token)}")
    
    # Run cloudflared using the token directly as argument
    cmd = [
        "cloudflared", "tunnel", "run",
        "--token", token
    ]
    
    if debug:
        print(f"Debug: Running command: {' '.join(cmd)}")
    
    process = subprocess.Popen(cmd, 
                             stdout=subprocess.PIPE if debug else None,
                             stderr=subprocess.PIPE if debug else None)
    
    zone_id = "a2dbaff918c783a734197864e6cb7190"  # Using the zone ID from the bash script
    
    # Clean up function to remove token file, terminate process, and cleanup cloudflare resources
    def cleanup():
        if os.path.exists(token_file):
            os.remove(token_file)
            if debug:
                print(f"Debug: Removed token file {token_file}")
        if process.poll() is None:
            process.terminate()
            if debug:
                print(f"Debug: Terminated cloudflared process")
        
        print("🧹 Cleaning up Cloudflare resources...")
        dns_records_deleted = delete_tunnel_and_dns(account_id, tunnel_id, tunnel_name, zone_id, debug)
        print(f"✅ Cleanup complete! Removed tunnel and {dns_records_deleted} DNS record(s)")
    
    # Register cleanup on exit
    atexit.register(cleanup)
    
    # Handle keyboard interrupt
    def signal_handler(sig, frame):
        if debug:
            print(f"Debug: Received signal {sig}, cleaning up")
        cleanup()
        sys.exit(0)
    
    signal.signal(signal.SIGINT, signal_handler)
    
    # If in debug mode, show initial output
    if debug:
        # Give the process a moment to start
        time.sleep(1)
        if process.poll() is not None:  # Process has already exited
            stdout, stderr = process.communicate()
            print(f"Debug: Process exited with code {process.returncode}")
            print(f"Debug: stdout: {stdout.decode() if stdout else 'None'}")
            print(f"Debug: stderr: {stderr.decode() if stderr else 'None'}")
        else:
            print(f"Debug: Process is running with PID {process.pid}")
    
    return process

def check_cloudflared_installed():
    try:
        subprocess.run(["cloudflared", "--version"], 
                      stdout=subprocess.PIPE, 
                      stderr=subprocess.PIPE)
        return True
    except FileNotFoundError:
        return False

def install_instructions():
    print("Error: cloudflared not found.")
    print("\nInstallation instructions:")
    print("  - Debian/Ubuntu: curl -L https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-linux-amd64.deb -o cloudflared.deb && sudo dpkg -i cloudflared.deb")
    print("  - macOS: brew install cloudflared")
    print("  - Others: Visit https://developers.cloudflare.com/cloudflare-one/connections/connect-apps/install-and-setup/installation")
    sys.exit(1)

def main():
    parser = argparse.ArgumentParser(description="Cloudflare tunnel wrapper that works like ngrok")
    parser.add_argument("tunnel_name", help="Name for the tunnel", nargs='?')
    parser.add_argument("port", type=int, help="Local port to expose")
    parser.add_argument("domain", nargs='?', help="Custom domain to use (e.g., example.com)")
    parser.add_argument("--debug", action="store_true", help="Enable debug mode")
    parser.add_argument("--local-addr", default="localhost", help="Local address to forward to (default: localhost)")
    parser.add_argument("--no-timestamp", action="store_true", help="Don't add timestamp to tunnel name")
    args = parser.parse_args()
    
    debug = args.debug
    
    if debug:
        print(f"Debug: Starting in debug mode")
        print(f"Debug: Python version: {sys.version}")
        print(f"Debug: System: {sys.platform}")
    
    if not check_cloudflared_installed():
        install_instructions()
    
    # Handle tunnel name and domain parameters
    port = args.port
    local_addr = args.local_addr
    custom_domain = args.domain
    
    # Handle auto-generated tunnel name case
    if args.tunnel_name is None:
        # Generate a random name if none provided
        random_name = ''.join(random.choices(string.ascii_lowercase, k=8))
        base_name = random_name
        tunnel_name = random_name
        print(f"🚀 Creating auto-named tunnel for {local_addr}:{port}...")
    else:
        base_name = args.tunnel_name
        # Add timestamp only if not using --no-timestamp flag
        if args.no_timestamp:
            tunnel_name = base_name
        else:
            timestamp = int(time.time())
            tunnel_name = f"{base_name}-{timestamp}"
        print(f"🚀 Creating tunnel '{base_name}' for {local_addr}:{port}...")
    
    try:
        # Check API key first
        api_key = get_api_key()
        if debug:
            if '@' in api_key:
                print(f"Debug: Using Global API Key (email:key format)")
            else:
                print(f"Debug: Using API Token format")
        
        account_id = get_account_id()
        
        if debug:
            print(f"Debug: Account ID: {account_id}")
            
        # With timestamped unique names, we don't need to check for existing tunnels
        if debug:
            print(f"Debug: Using unique tunnel name: {tunnel_name}")
            
        # Create a new tunnel with credentials
        tunnel_id, token_file = create_tunnel_with_credentials(account_id, tunnel_name, debug)
        
        if debug:
            print(f"Debug: Created tunnel with ID: {tunnel_id}")
            
        hostname, _ = create_tunnel_config(account_id, tunnel_id, tunnel_name, port, local_addr, custom_domain, debug)
        
        print(f"✅ Tunnel created successfully!")
        print(f"🌐 Public URL: https://{hostname}")
        print(f"⚡ Forwarding to: {local_addr}:{port}")
        print("🔄 Starting cloudflared tunnel client...")
        print("🛑 Press Ctrl+C to stop")
        
        process = run_cloudflared(token_file, None, tunnel_id, account_id, tunnel_name, debug)
        
        # Wait for the process to finish
        try:
            process.wait()
        except KeyboardInterrupt:
            print("\n🛑 Stopping tunnel...")
            sys.exit(0)
    except requests.RequestException as e:
        print(f"❌ Network error: {str(e)}")
        if debug:
            import traceback
            traceback.print_exc()
        sys.exit(1)
    except Exception as e:
        print(f"❌ Error: {str(e)}")
        if debug:
            import traceback
            traceback.print_exc()
        sys.exit(1)