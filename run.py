from backend.app import create_app

app = create_app()

if __name__ == '__main__':
    app.run(debug=True, port=5050)

for rule in app.url_map.iter_rules():
    print(f"{rule} --> {rule.endpoint}")
