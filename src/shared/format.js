export const formatKg = (value = 0) => new Intl.NumberFormat('es-PE').format(value)
export const priorityClass = (priority = '') => priority.toLowerCase().replace('alta', 'high').replace('media', 'mid').replace('baja', 'low')
