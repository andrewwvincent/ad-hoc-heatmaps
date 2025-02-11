import http.server
import socketserver
import os
import sys
from functools import partial

class CORSHTTPRequestHandler(http.server.SimpleHTTPRequestHandler):
    def end_headers(self):
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET')
        self.send_header('Cache-Control', 'no-store, no-cache, must-revalidate')
        return super().end_headers()
        
    def handle_one_request(self):
        try:
            return super().handle_one_request()
        except ConnectionAbortedError:
            print("Client connection aborted, continuing to serve...")
        except Exception as e:
            print(f"Error handling request: {e}")

if __name__ == '__main__':
    PORT = 5000
    
    # Change to the directory containing this script
    os.chdir(os.path.dirname(os.path.abspath(__file__)))
    
    Handler = partial(CORSHTTPRequestHandler, directory=os.getcwd())
    
    while True:
        try:
            with socketserver.TCPServer(("", PORT), Handler) as httpd:
                print(f"Serving at port {PORT}...")
                httpd.serve_forever()
        except OSError as e:
            if e.errno == 98:  # Address already in use
                print(f"Port {PORT} is in use, trying {PORT + 1}")
                PORT += 1
            else:
                raise e
        except KeyboardInterrupt:
            print("\nShutting down server...")
            sys.exit(0)
        except Exception as e:
            print(f"Server error: {e}")
            print("Restarting server...")
            continue
