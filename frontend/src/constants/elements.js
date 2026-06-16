export const ELEMENT_COLORS = {
  paragraph: { bg: 'rgba(24, 144, 255, 0.2)', border: '#1890ff', label: '正文' },
  title: { bg: 'rgba(255, 77, 79, 0.2)', border: '#ff4d4f', label: '标题' },
  table: { bg: 'rgba(82, 196, 26, 0.2)', border: '#52c41a', label: '表格' },
  figure: { bg: 'rgba(250, 173, 20, 0.2)', border: '#faad14', label: '图片' },
  caption: { bg: 'rgba(114, 46, 209, 0.2)', border: '#722ed1', label: '图注' },
  header: { bg: 'rgba(235, 47, 150, 0.2)', border: '#eb2f96', label: '页眉' },
  footer: { bg: 'rgba(19, 194, 194, 0.2)', border: '#13c2c2', label: '页脚' },
  page_number: { bg: 'rgba(250, 240, 137, 0.3)', border: '#faad14', label: '页码' },
  list: { bg: 'rgba(250, 84, 28, 0.2)', border: '#fa541c', label: '列表' },
  formula: { bg: 'rgba(47, 84, 235, 0.2)', border: '#2f54eb', label: '公式' },
  stamp: { bg: 'rgba(217, 45, 32, 0.2)', border: '#d92d20', label: '印章' },
};

export const ELEMENT_TYPES = [
  { value: 'paragraph', label: '正文段落' },
  { value: 'title', label: '标题' },
  { value: 'table', label: '表格' },
  { value: 'figure', label: '图片' },
  { value: 'caption', label: '图注' },
  { value: 'header', label: '页眉' },
  { value: 'footer', label: '页脚' },
  { value: 'page_number', label: '页码' },
  { value: 'list', label: '列表' },
  { value: 'formula', label: '公式' },
  { value: 'stamp', label: '印章/签名' },
];

export const TASK_STATUS = {
  pending: { text: '排队中', color: 'default' },
  processing: { text: '处理中', color: 'processing' },
  completed: { text: '已完成', color: 'success' },
  failed: { text: '失败', color: 'error' },
};

export function getElementColor(type) {
  return ELEMENT_COLORS[type] || ELEMENT_COLORS.paragraph;
}
