from flask import Flask, request, jsonify, send_from_directory
from pathlib import Path
import json
import os
import main as main_module

# static files moved to `web/` directory — serve from there
app = Flask(__name__, static_folder='web', static_url_path='')


@app.route('/')
def index():
    return send_from_directory(app.static_folder, 'webpage.html')


@app.route('/<path:filename>')
def static_files(filename):
    return send_from_directory(app.static_folder, filename)


@app.route('/submit', methods=['POST'])
def submit():
    data = request.get_json()
    if not data:
        return jsonify({'error': 'no json body provided'}), 400

    # write input.json to disk (as requested)
    input_path = Path('input_sample.json')
    input_path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding='utf-8')

    try:
        result = main_module.process_input(str(input_path))
    except Exception as e:
        return jsonify({'error': str(e)}), 500

    return jsonify(result)


if __name__ == '__main__':
    # dev server
    app.run(host='0.0.0.0', port=5000, debug=True)
