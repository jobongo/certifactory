import client from './client'

export const getCertificates = async (params = {}) => {
  const { data } = await client.get('/certificates', { params })
  return data
}

export const getCertificate = async (id) => {
  const { data } = await client.get(`/certificates/${id}`)
  return data
}

export const createCertificate = async (certData) => {
  const { data } = await client.post('/certificates', certData)
  return data
}

export const submitCSR = async (csrData) => {
  const { data } = await client.post('/certificates/csr', csrData)
  return data
}

export const approveCert = async (id) => {
  const { data } = await client.post(`/certificates/${id}/approve`)
  return data
}

export const denyCert = async (id) => {
  const { data } = await client.post(`/certificates/${id}/deny`)
  return data
}

export const revokeCert = async (id, reason) => {
  const { data } = await client.post(`/certificates/${id}/revoke`, { reason })
  return data
}

export const renewCert = async (id) => {
  const { data } = await client.post(`/certificates/${id}/renew`)
  return data
}

export const deleteCert = async (id) => {
  await client.delete(`/certificates/${id}`)
}

export const downloadCert = async (id, format, passphrase, keyOnly = false) => {
  const params = { format }
  if (passphrase) params.passphrase = passphrase
  if (keyOnly) params.key_only = true
  const { data } = await client.get(`/certificates/${id}/download`, {
    params,
    responseType: 'blob',
  })
  return data
}
