#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Wed Aug 21 10:51 2024

@author: mikhailkruger
"""

from flask import Flask, render_template

app = Flask(__name__)

@app.route('/')
def index():
    return render_template('index_1.html')

if __name__ == '__main__':
    app.run(debug=True, port = 5002)