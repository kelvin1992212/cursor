export function formatDateTime(value) {
  if (!value) return "-";
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return value;
  return date.toLocaleString();
}

export function channelLabel(channel) {
  const labels = {
    whatsapp: "WhatsApp",
    wechat: "WeChat",
    facebook: "Facebook",
    instagram: "Instagram",
  };
  return labels[channel] || channel;
}
