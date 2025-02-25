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
        
    return render_template('criarconta.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        nome = request.form['nome']
        senha = request.form['senha']

        try:
            response = supabase.table('usuarios').select('id', 'nome', 'senha', 'email').eq('nome', nome).execute()
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
                flash("Nome não encontrado. Verifique e tente novamente.", "error")
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

@app.route('/add_especialidade', methods=['GET', 'POST'])
def add_especialidade():
    if 'nome' not in session:
        flash("Você precisa estar logado para acessar esta página.", "warning")
        return redirect(url_for('login'))

    # Consultando os membros (usuários)
    membros = supabase.table('usuarios').select('id', 'nome').execute().data

    if request.method == 'POST':
        membro_id = request.form['membro_id']
        especialidade = request.form['especialidade']
        
        # Inserindo a especialidade na tabela 'especialidades' com o usuario_id
        supabase.table('especialidades').insert({
            "usuario_id": membro_id,
            "especialidade": especialidade
        }).execute()

        flash(f'Especialidade {especialidade} adicionada ao membro com sucesso!', 'success')
        return redirect(url_for('add_especialidade'))

    return render_template('add_especialidade.html', membros=membros)

@app.route('/detalhes_usuario/<int:user_id>')
def detalhes_usuario(user_id):
    if 'nome' not in session:
        flash("Você precisa estar logado para acessar esta página.", "warning")
        return redirect(url_for('login'))

    nome = session['nome']
    cargo = session.get('cargo')
    email = session.get('email', 'Email Desconhecido')
    data_nasc = session.get('data_nasc', 'Não Informado')
    especialidades = []

    try:
        # Carregar o cargo do banco de dados, caso não esteja na sessão
        if not cargo:
            response = supabase.table('usuarios').select('cargo').eq('id', user_id).execute()
            if response.data:
                cargo = response.data[0]['cargo']
                session['cargo'] = cargo  # Salvando o cargo na sessão

        # Carregar os dados do usuário
        usuario_response = supabase.table('usuarios').select('nome', 'data_nasc', 'email').eq('id', user_id).execute()

        if usuario_response.data:
            usuario = usuario_response.data[0]
            nome_usuario = usuario.get('nome', 'Nome não encontrado.')
            data_nasc = usuario.get('data_nasc', 'Não Informado')
            email = usuario.get('email', 'Email não encontrado.')
        else:
            nome_usuario = 'Nome não encontrado.'
            data_nasc = 'Não Informado'
            email = 'Email não encontrado.'

        # Carregar as especialidades
        especialidades_response = supabase.table('especialidades').select('especialidade').eq('usuario_id', user_id).execute()

        if especialidades_response.data:
            especialidades = [item['especialidade'] for item in especialidades_response.data]

        # Associar as especialidades ao usuário
        usuario['especialidades'] = especialidades

    except Exception as e:
        flash(f"Erro ao carregar detalhes do usuário: {str(e)}", "error")
        nome_usuario = 'Erro ao carregar nome'
        cargo = 'Erro ao carregar cargo'
        especialidades = []
        data_nasc = 'Erro ao carregar data de nascimento'
        email = 'Erro ao carregar email'

    return render_template('membro_detalhes.html', nome=nome_usuario, cargo=cargo, email=email, id=user_id, especialidades=especialidades, data_nasc=data_nasc)


@app.route('/add_membro', methods=['GET', 'POST'])
def add_membro():
    if request.method == 'POST':
        nome = request.form['nome']
        email = request.form['email']
        senha = request.form['senha']

        senha_hash = generate_password_hash(senha)

        data = {'nome': nome, 'email': email, 'senha': senha_hash}

        try:
            supabase.table('usuarios').insert([data]).execute()
            flash(f'Membro {nome} adicionado com sucesso!', 'success')
            return redirect(url_for('diretoria'))
        except Exception as e:
            flash(f"Erro ao adicionar membro: {str(e)}", "error")
            return redirect(url_for('add_membro'))

    return render_template('add_membro.html')

@app.route('/unidade', methods=['GET', 'POST'])
def unidade():
    return render_template('unidade.html')


@app.route('/perfil')
def perfil():
    if 'usuario_id' not in session:
        return redirect(url_for('login'))

    usuario_id = session.get('usuario_id')
    nome = session.get('nome', 'Usuário Desconhecido')
    cargo = session.get('cargo')
    email = session.get('email', 'Email Desconhecido')
    data_nasc = session.get('data_nasc', 'Não Informado')
    especialidades = []  # Começa com uma lista vazia

    try:
        if not cargo:
            response = supabase.table('usuarios').select('cargo').eq('id', usuario_id).execute()
            if response.data:
                cargo = response.data[0]['cargo']
                session['cargo'] = cargo  # Salvando o cargo na sessão

        usuario_response = supabase.table('usuarios').select('nome', 'data_nasc').eq('id', usuario_id).execute()

        if usuario_response.data:
            nome_usuario = usuario_response.data[0].get('nome', 'Nome não encontrado.')
            data_nasc = usuario_response.data[0].get('data_nasc', 'Não Informado')
        else:
            nome_usuario = 'Nome não encontrado.'
            data_nasc = 'Não Informado'

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
        data_nasc = 'Erro ao carregar data de nascimento'

    return render_template('perfil.html', nome=nome_usuario, cargo=cargo, email=email, id=usuario_id, especialidades=especialidades, data_nasc=data_nasc)

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
