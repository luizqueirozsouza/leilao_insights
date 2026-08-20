## Purpose

Permite que usuários criem conta, façam login e logout por email e senha, estabelecendo identidade para controle de acesso e assinaturas.

## ADDED Requirements

### Requirement: Registro de usuário
O sistema SHALL permitir que um usuário crie uma conta informando email e senha, validando a unicidade do email.

#### Scenario: Registro bem-sucedido
- **WHEN** um visitante informa um email válido e uma senha válida para se cadastrar
- **THEN** o sistema cria a conta, autentica o usuário e o redireciona para a área autenticada

#### Scenario: Registro com email duplicado
- **WHEN** um visitante tenta se cadastrar com um email já existente
- **THEN** o sistema exibe erro de email já cadastrado e não cria a conta

### Requirement: Login e logout
O sistema SHALL permitir que um usuário autentique-se com email e senha e que encerre a sessão a qualquer momento.

#### Scenario: Login com credenciais corretas
- **WHEN** um usuário informa email e senha corretos
- **THEN** o sistema inicia uma sessão autenticada e libera os recursos restritos

#### Scenario: Login com credenciais inválidas
- **WHEN** um usuário informa email ou senha incorretos
- **THEN** o sistema exibe erro de credenciais inválidas e não autentica o usuário

#### Scenario: Logout
- **WHEN** um usuário autenticado encerra a sessão
- **THEN** o sistema invalida a sessão e retorna o usuário ao estado de visitante

### Requirement: Sessão persistente
O sistema SHALL manter a sessão autenticada do usuário entre requisições e recarregamentos de página.

#### Scenario: Usuário recarrega a página
- **WHEN** um usuário autenticado recarrega a página
- **THEN** o sistema mantém o usuário autenticado e continua exibindo recursos restritos
