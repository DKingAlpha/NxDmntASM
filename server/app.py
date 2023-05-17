#!/usr/bin/python3
#-*- coding:utf-8 -*-

import sys
from pathlib import Path
sys.path.insert(0, Path(__file__).parent.parent.as_posix())

from flask import Flask, render_template, request, jsonify
from dmnt_asm.parser import CheatParser

app = Flask(__name__)

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/dmnt_dism', methods=['POST'])
def dmnt_dism():
    text = request.form['text']
    # Perform any processing on the text if needed
    errors = []
    def err_handler(msg):
        nonlocal errors
        errors.append(msg)
    p = CheatParser(err_handler)
    all_ok = p.load(text)
    dism = p.dism(indent=4)
    return jsonify({
        'success': all_ok,
        'dism': dism,
        'errors': errors
    })


@app.route('/dmnt_asm', methods=['POST'])
def dmnt_asm():
    text = request.form['text']
    # Perform any processing on the text if needed
    errors = []
    def err_handler(msg):
        nonlocal errors
        errors.append(msg)
    p = CheatParser(err_handler)
    all_ok = p.load(text)
    asm = p.asm(indent=4)
    return jsonify({
        'success': all_ok,
        'asm': asm,
        'errors': errors
    })


if __name__ == '__main__':
    app.run(host="0.0.0.0", debug=False)
