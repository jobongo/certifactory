import client from './client'

export const getUsers = async (page = 1, perPage = 25) => {
  const { data } = await client.get('/users', { params: { page, per_page: perPage } })
  return data
}

export const createUser = async (userData) => {
  const { data } = await client.post('/users', userData)
  return data
}

export const getUser = async (id) => {
  const { data } = await client.get(`/users/${id}`)
  return data
}

export const updateUser = async (id, userData) => {
  const { data } = await client.put(`/users/${id}`, userData)
  return data
}

export const deleteUser = async (id) => {
  await client.delete(`/users/${id}`)
}

export const resetUserPassword = async (id, password) => {
  const { data } = await client.put(`/users/${id}/reset-password`, { password })
  return data
}
