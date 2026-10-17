import os

def generate():
    css_bloat = '\n'.join([f'.rule_{i} {{ color: #{i:06x}; margin: {i}px; padding: 10px; }}' for i in range(2500)])
    dom_bloat = '\n'.join([f'<div class="box rule_{i}"><span>Item {i}</span><b>Detail {i}</b><i>Note {i}</i><u>Status {i}</u></div>' for i in range(400)])

    html = f"""<!DOCTYPE html>
<html>
<head>
    <title>Bloated Anti-Pattern Site - PageLens Fixture</title>
    <script src="http://cdn.insecure.com/tracker.js"></script>
    <script src="https://code.jquery.com/jquery-1.11.1.min.js"></script>
    <script src="https://maxcdn.bootstrapcdn.com/bootstrap/3.3.7/js/bootstrap.min.js"></script>
    <style>
{css_bloat}
    </style>
</head>
<body>
    <h1>Severely Degraded Anti-Pattern Webpage</h1>
    <p>This fixture contains active mixed content, excessive DOM elements, vulnerable legacy dependencies, and unencrypted form endpoints.</p>
    <form action="http://insecure-endpoint.com/login" method="POST">
        <input type="text" name="user">
        <input type="password" name="pass">
        <button type="submit">Submit Insecurely</button>
    </form>
    <img src="http://cdn.insecure.com/insecure-img.png" alt="Insecure Mixed Content Image">
    <img src="https://images.example.com/huge-uncompressed-photo.jpg" alt="Uncompressed image">
    <img src="https://images.example.com/banner-no-dims.jpg" alt="No dimensions banner">
    <div id="dom-heavy-container">
{dom_bloat}
    </div>
</body>
</html>"""

    fixtures_dir = os.path.dirname(os.path.abspath(__file__))
    target = os.path.join(fixtures_dir, "bad_site.html")
    with open(target, "w", encoding="utf-8") as f:
        f.write(html)
    print(f"Generated {target} (size: {len(html)} bytes)")

if __name__ == "__main__":
    generate()
