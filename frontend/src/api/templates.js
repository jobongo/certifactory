import client from './client'

export const getTemplates = async (caId) => {
  const { data } = await client.get(`/cas/${caId}/templates`)
  return data
}

export const createTemplate = async (caId, template) => {
  const { data } = await client.post(`/cas/${caId}/templates`, template)
  return data
}

export const updateTemplate = async (caId, templateId, template) => {
  const { data } = await client.put(`/cas/${caId}/templates/${templateId}`, template)
  return data
}

export const deleteTemplate = async (caId, templateId) => {
  await client.delete(`/cas/${caId}/templates/${templateId}`)
}
