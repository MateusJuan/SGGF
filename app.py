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

# Conexão com Supabase
url = os.getenv("SUPABASE_URL", "https://htqnxhtlzjcinjjzbosm.supabase.co")
key = os.getenv("SUPABASE_KEY", "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6Imh0cW54aHRsempjaW5qanpib3NtIiwicm9sZSI6ImFub24iLCJpYXQiOjE3MzU3NTA5NTksImV4cCI6MjA1MTMyNjk1OX0.AslApaKGVWrg8lETjxbD-8seA10GbvrRQkxVNjoqDSU")
supabase: Client = create_client(url, key)


@app.before_request
def verificar_login():
    if 'nome' not in session and request.endpoint not in ['login', 'criar_conta']:
        return redirect(url_for('login'))


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

        response = supabase.table('usuarios').select('id').eq('email', email).execute()
        if response.data:
            flash("Este email já está registrado.", "error")
            return redirect(url_for('criar_conta'))

        senha_hash = generate_password_hash(senha)
        data = {'nome': nome, 'email': email, 'senha': senha_hash}

        try:
            supabase.table('usuarios').insert([data]).execute()
            flash("Conta criada com sucesso!", "success")
            return redirect(url_for('login'))
        except Exception as e:
            flash(f"Erro ao criar conta: {str(e)}", "error")
            return redirect(url_for('criar_conta'))

    return render_template('login.html')


@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form['email']
        senha = request.form['senha']

        try:
            response = supabase.table('usuarios').select('id', 'email', 'senha', 'nome').eq('email', email).execute()
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
            flash(f"Erro ao processar o login: {str(e)}", "error")

    return render_template('login.html')


@app.route('/logout')
def logout():
    session.clear()
    flash("Você foi desconectado com sucesso.", "success")
    return redirect(url_for('login'))


@app.route('/')
def home():
    if 'nome' not in session:
        return redirect(url_for('login'))
    nome = session['nome']
    cargo = session.get('cargo')

    if not cargo:
        try:
            response = supabase.table('usuarios').select('cargo').eq('nome', nome).execute()
            if response.data:
                cargo = response.data[0]['cargo']
                session['cargo'] = cargo
            else:
                cargo = None
        except Exception as e:
            flash(f"Erro ao carregar o cargo: {str(e)}", "error")
            cargo = None
    
    return render_template('index.html', nome=nome, cargo=cargo)

@app.route('/diretoria')
def diretoria():
    if 'nome' not in session:
        flash("Você precisa estar logado para acessar esta página.", "warning")
        return redirect(url_for('login'))

    nome = session['nome']
    membros = []

    try:
        usuarios_response = supabase.table('usuarios').select('id', 'nome').order('nome').execute()

        if usuarios_response.data:
            membros = usuarios_response.data
        else:
            flash("Não há membros registrados.", "info")

    except Exception as e:
        flash(f"Erro ao carregar membros: {str(e)}", "error")
        print("Erro ao carregar membros:", str(e))

    return render_template('diretoria.html', nome=nome, membros=membros)

@app.route('/detalhes_usuario/<int:user_id>')
def detalhes_usuario(user_id):
    if 'nome' not in session:
        flash("Você precisa estar logado para acessar esta página.", "warning")
        return redirect(url_for('login'))

    nome = session['nome']
    usuario = None
    especialidades = []

    try:
        usuario_response = supabase.table('usuarios').select('*').eq('id', user_id).execute()

        if usuario_response.data:
            usuario = usuario_response.data[0]

            especialidades_response = supabase.table('especialidades').select('especialidade').eq('usuario_id', user_id).execute()

            if especialidades_response.data:
                especialidades = [item['especialidade'] for item in especialidades_response.data]

            usuario['especialidades'] = especialidades
        else:
            flash("Usuário não encontrado.", "info")

    except Exception as e:
        flash(f"Erro ao carregar detalhes do usuário: {str(e)}", "error")
        print("Erro ao carregar detalhes do usuário:", str(e))

    return render_template('membro_detalhes.html', nome=nome, membro=usuario)


@app.route('/perfil')
def perfil():
    if 'usuario_id' not in session:
        return redirect(url_for('login'))

    usuario_id = session.get('usuario_id')
    nome = session.get('nome', 'Usuário Desconhecido')
    cargo = session.get('cargo')
    email = session.get('email', 'Email Desconhecido')

    especialidades = []  # Começa com uma lista vazia

    try:
        if not cargo:
            response = supabase.table('usuarios').select('cargo').eq('id', usuario_id).execute()
            if response.data:
                cargo = response.data[0]['cargo']
                session['cargo'] = cargo  # Salvando o cargo na sessão

        usuario_response = supabase.table('usuarios').select('nome').eq('id', usuario_id).execute()

        if usuario_response.data:
            nome_usuario = usuario_response.data[0].get('nome', 'Nome não encontrado.')
        else:
            nome_usuario = 'Nome não encontrado.'

        especialidades_response = supabase.table('especialidades').select('especialidade').eq('usuario_id', usuario_id).execute()

        if especialidades_response.data:
            especialidades = [item['especialidade'] for item in especialidades_response.data]
        else:
            especialidades = []

    except Exception as e:
        flash(f"Erro ao carregar dados: {str(e)}", "error")
        nome_usuario = 'Erro ao carregar nome'
        cargo = 'Erro ao carregar cargo'
        especialidades = []

    return render_template('perfil.html', nome=nome_usuario, cargo=cargo, email=email, id=usuario_id, especialidades=especialidades)

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
