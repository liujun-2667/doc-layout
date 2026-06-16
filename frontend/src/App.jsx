import React from 'react';
import { Routes, Route, Link } from 'react-router-dom';
import { Layout, Menu } from 'antd';
import { FileTextOutlined, SettingOutlined } from '@ant-design/icons';
import TaskList from './pages/TaskList';
import TaskDetail from './pages/TaskDetail';
import Proofread from './pages/Proofread';

const { Header, Content, Sider } = Layout;

const menuItems = [
  {
    key: 'tasks',
    icon: <FileTextOutlined />,
    label: <Link to="/">任务管理</Link>,
  },
];

function App() {
  return (
    <Layout className="layout-container">
      <Header className="page-header" style={{ display: 'flex', alignItems: 'center', padding: '0 24px' }}>
        <div style={{ color: '#fff', fontSize: 20, fontWeight: 'bold', marginRight: 40 }}>
          📄 文档版面分析系统
        </div>
        <Menu
          theme="dark"
          mode="horizontal"
          defaultSelectedKeys={['tasks']}
          items={menuItems}
          style={{ flex: 1, minWidth: 0 }}
        />
      </Header>
      <Content className="page-content" style={{ padding: '24px' }}>
        <Routes>
          <Route path="/" element={<TaskList />} />
          <Route path="/tasks/:taskId" element={<TaskDetail />} />
          <Route path="/tasks/:taskId/proofread" element={<Proofread />} />
        </Routes>
      </Content>
    </Layout>
  );
}

export default App;
