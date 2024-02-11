from flask import Flask, render_template, request
from model import GPT2PPL

app = Flask(__name__)

# Initialize the GPT2PPL model
gpt2_model = GPT2PPL()

@app.route('/')
def index():
    return render_template('templates/index.html')

@app.route('/', methods=['POST'])
def predict():
    if request.method == 'POST':
        prompt = request.form['prompt']
        results, output = gpt2_model(prompt)
        return render_template('templates/index.html', prompt=prompt, output=output, results=results)

if __name__ == '__main__':
    app.run(debug=True)
