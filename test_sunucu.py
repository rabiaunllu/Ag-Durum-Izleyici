import http.server
import socketserver

PORT = 8000
handler = http.server.SimpleHTTPRequestHandler

with socketserver.TCPServer(("", PORT), handler) as httpd:
    print(f"Sunucu {PORT} portunda çalışıyor... Kapatmak için terminalde Ctrl+C yap!")
    httpd.serve_forever()