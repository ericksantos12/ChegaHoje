---
name: Feature Spec (Lite)
about: Especificação enxuta para melhorias ou features pequenas
title: "[Feature] <nome da feature>"
labels: ["feature"]
assignees: []
---

# ✨ Feature: <nome da feature>

## 🧾 Resumo
Descreva rapidamente o que será implementado.

Exemplo:  
Adicionar filtro por status na listagem de pedidos.

---

## ❗ Problema
Qual problema isso resolve?

Exemplo:  
Hoje não é possível filtrar pedidos concluídos ou cancelados, dificultando a análise da lista.

---

## 🎯 Objetivo
Qual resultado essa melhoria deve gerar?

Exemplo:  
Permitir que o usuário filtre pedidos por status diretamente na interface.

---

## 📦 Escopo

### ✅ Dentro
- Filtro por status na UI
- Parâmetro de filtro na API
- Atualização da listagem com base no filtro

### ❌ Fora
- Paginação nova
- Ordenação avançada
- Exportação de resultados

---

## 📜 Regras de negócio
- O filtro deve aceitar apenas valores válidos do enum de status
- Quando nenhum filtro for informado, retornar todos os resultados
- Filtro deve ser aplicado no backend

---

## ✅ Critérios de aceite

- [ ] Usuário consegue selecionar um status no filtro
- [ ] A API aceita parâmetro `status`
- [ ] A lista retorna apenas registros com o status selecionado
- [ ] Filtro persiste durante navegação da página

---

## 🧩 Tasks

### 🖥 Backend
- [ ] Adicionar parâmetro `status` no endpoint
- [ ] Validar valores permitidos
- [ ] Aplicar filtro na query

### 🎨 Frontend
- [ ] Adicionar dropdown de status
- [ ] Enviar filtro na requisição
- [ ] Atualizar listagem ao mudar filtro

### 🧪 Testes
- [ ] Teste unitário do filtro
- [ ] Teste de integração do endpoint

---

## 💻 Exemplo técnico

### Endpoint

```ts
import { Request, Response } from "express";

export async function listOrders(req: Request, res: Response): Promise<void> {
  const status = req.query.status as string | undefined;

  const allowedStatus = ["pending", "completed", "cancelled"];

  if (status && !allowedStatus.includes(status)) {
    res.status(400).json({
      error: "invalid_status"
    });
    return;
  }

  const orders = await findOrders(status);

  res.json({
    data: orders
  });
}

async function findOrders(status?: string) {
  if (!status) {
    return [];
  }

  return [];
}
