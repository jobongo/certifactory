import client from './client'

export const login = async (username, password) => {
  const { data } = await client.post('/auth/login', { username, password })
  return data
}

export const getMe = async () => {
  const { data } = await client.get('/auth/me')
  return data
}

export const changePassword = async (currentPassword, newPassword) => {
  const { data } = await client.put('/auth/me/password', {
    current_password: currentPassword,
    new_password: newPassword,
  })
  return data
}
