// 統一的聯絡資訊管理
// 作為整個應用程式的唯一聯絡資訊來源

export const CONTACT_DATA = [
  { name: 'Yuan-Tung Chou', email: 'ton731@gmail.com' },
  { name: 'Chien-Yu Tseng', email: 'cy12tseng@gmail.com' },
  { name: 'I-Hsiang Chang', email: 'ckbxkyle@gmail.com' },
  { name: 'Shih-Hao Tseng', email: 'max87520987@gmail.com' }
];

// 為 ChatBot 格式化為 Markdown 格式
export const getFormattedContactInfo = () => {
  return `**Development Team**

This platform was developed by:

${CONTACT_DATA.map(contact => `**${contact.name}**\n${contact.email}`).join('\n\n')}

Feel free to reach out for any questions or feedback about the platform!`;
};

// 為其他組件回傳原始陣列格式
export const getContactArray = () => {
  return CONTACT_DATA;
};