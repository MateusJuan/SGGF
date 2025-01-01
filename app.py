from flask import Flask, render_template, request, redirect, url_for, session, flash
import os
from datetime import timedelta
from supabase import create_client, Client
from werkzeug.security import check_password_hash, generate_password_hash
from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__, static_folder='static', template_folder='templates')
app.secret_key = os.urandom(24)
app.config['PERMANENT_SESSION_LIFETIME'] = timedelta(days=30)

# Carregando as variáveis de ambiente para conectar ao Supabase
url = os.getenv("SUPABASE_URL", "https://htqnxhtlzjcinjjzbosm.supabase.co")
key = os.getenv("SUPABASE_KEY", "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6Imh0cW54aHRsempjaW5qanpib3NtIiwicm9sZSI6ImFub24iLCJpYXQiOjE3MzU3NTA5NTksImV4cCI6MjA1MTMyNjk1OX0.AslApaKGVWrg8lETjxbD-8seA10GbvrRQkxVNjoqDSU")
supabase: Client = create_client(url, key)

@app.before_request
def verificar_login():
    if 'nome' not in session and request.endpoint not in ['login', 'criar_conta']:
        return redirect(url_for('login'))

##########################################################################################################
@app.route('/criar_conta', methods=['GET', 'POST'])
def criar_conta():
    if request.method == 'POST':
        nome = request.form['nome']
        email = request.form['email']
        senha = request.form['senha']
        senha_confirmacao = request.form['senha_confirmacao']

        if senha != senha_confirmacao:
            flash("As senhas não coincidem.", "error")
            return redirect(url_for('criar_conta'))

        # Verificando se o email já está registrado
        response = supabase.table('usuarios').select('id').eq('email', email).execute()
        print(f"Resposta da verificação de email: {response}")  # Debugging

        if response.data:
            flash("Este email já está registrado.", "error")
            return redirect(url_for('criar_conta'))

        # Gerando o hash da senha
        senha_hash = generate_password_hash(senha)
        data = {'nome': nome, 'email': email, 'senha': senha_hash}

        try:
            # Teste de conexão antes de tentar inserir
            test_response = supabase.table('usuarios').select('*').execute()
            print(f"Testando conexão com a tabela 'usuarios': {test_response}")  # Verificando a tabela

            # Tentando inserir o usuário na tabela 'usuarios'
            response = supabase.table('usuarios').insert([data]).execute()
            print(f"Resposta da inserção: {response}")  # Depuração

            # Verificando a resposta da inserção
            if response.status_code == 201 or response.status_code == 200:
                flash("Conta criada com sucesso!", "success")
                return redirect(url_for('login'))
            else:
                flash(f"Erro ao criar conta: {response.data}", "error")
                return redirect(url_for('criar_conta'))
        except Exception as e:
            flash(f"Erro ao criar conta: {str(e)}", "error")
            print(f"Erro ao criar conta: {str(e)}")  # Log de erro
            return redirect(url_for('criar_conta'))

    return render_template('login.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form['email']
        senha = request.form['senha']
        try:
            response = supabase.table('usuarios').select('id', 'email', 'senha', 'nome').eq('email', email).execute()
            print(f"Resposta do login: {response}")  # Debugging

            if response.data:
                usuario = response.data[0]

                if check_password_hash(usuario['senha'], senha):
                    session['nome'] = usuario['nome']
                    session['usuario_id'] = usuario['id']
                    session['email'] = usuario['email']

                    flash(f"Bem-vindo, {usuario['nome']}!", "success")
                    return redirect(url_for('home'))
                else:
                    flash("Senha incorreta. Tente novamente.", "error")
            else:
                flash("Email não encontrado. Verifique e tente novamente.", "error")
        except Exception as e:
            print("Erro ao realizar login:", str(e))
            flash("Ocorreu um erro ao processar seu login. Tente novamente mais tarde.", "error")

    return render_template('login.html')

@app.route('/logout')
def logout():
    session.clear()
    flash("Você foi desconectado com sucesso.", "success")
    return redirect(url_for('login'))

###########################################################################################################

@app.route('/')
def home():
    if 'nome' not in session:
        return redirect(url_for('login'))

    nome = session['nome']
    return render_template('index.html', nome=nome)

@app.route('/perfil')
def perfil():
    if 'nome' not in session:
        return redirect(url_for('login'))

    nome = session['nome']
    email = session['email']
    usuario_id = session['usuario_id']
    return render_template('perfil.html', nome=nome, email=email, id=usuario_id)

@app.route('/trocarSenha', methods=['GET', 'POST'])
def trocarSenha():
    if 'usuario_id' not in session:
        return redirect(url_for('login'))

    if request.method == 'POST':
        senha_atual = request.form['senha_atual']
        nova_senha = request.form['nova_senha']
        confirmar_nova_senha = request.form['confirmar_nova_senha']

        response = supabase.table('usuarios').select('senha').eq('id', session['usuario_id']).execute()
        if not response.data:
            flash("Erro ao localizar o usuário.", "error")
            return redirect(url_for('trocarSenha'))

        senha_armazenada = response.data[0]['senha']
        if not check_password_hash(senha_armazenada, senha_atual):
            flash("Senha atual incorreta.", "error")
            return redirect(url_for('trocarSenha'))

        if nova_senha != confirmar_nova_senha:
            flash("A nova senha e a confirmação não coincidem.", "error")
            return redirect(url_for('trocarSenha'))

        nova_senha_hash = generate_password_hash(nova_senha, method='pbkdf2:sha256')
        supabase.table('usuarios').update({'senha': nova_senha_hash}).eq('id', session['usuario_id']).execute()

        flash("Senha alterada com sucesso!", "success")
        return redirect(url_for('perfil'))

    return render_template('mudar_senha.html')




if __name__ == '__main__':
    app.run(debug=True)