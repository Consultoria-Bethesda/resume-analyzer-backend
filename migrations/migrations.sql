-- Adiciona colunas para verificação de email
ALTER TABLE users
ADD COLUMN IF NOT EXISTS email_verification_token VARCHAR,
ADD COLUMN IF NOT EXISTS email_verification_expires TIMESTAMP;

-- Adiciona colunas para reset de senha (caso ainda não existam)
ALTER TABLE users
ADD COLUMN IF NOT EXISTS reset_password_token VARCHAR,
ADD COLUMN IF NOT EXISTS reset_password_expires TIMESTAMP;

-- Adiciona coluna para Stripe (caso ainda não exista)
ALTER TABLE users
ADD COLUMN IF NOT EXISTS stripe_customer_id VARCHAR;
