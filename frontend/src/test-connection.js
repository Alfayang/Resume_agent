// 测试前端与后端的连接
export const testBackendConnection = async () => {
  try {
    console.log('测试后端连接...');
    
    // 测试健康检查端点
    const healthResponse = await fetch('/api/health');
    if (healthResponse.ok) {
      const healthData = await healthResponse.json();
      console.log('✅ 后端健康检查成功:', healthData);
    } else {
      console.error('❌ 后端健康检查失败:', healthResponse.status);
    }
    
    // 测试状态列表端点
    const statesResponse = await fetch('/api/states');
    if (statesResponse.ok) {
      const statesData = await statesResponse.json();
      console.log('✅ 状态列表获取成功:', statesData);
    } else {
      console.error('❌ 状态列表获取失败:', statesResponse.status);
    }
    
  } catch (error) {
    console.error('❌ 连接测试失败:', error);
  }
};

// 测试特定trace_id的状态
export const testStateEndpoint = async (traceId) => {
  try {
    console.log(`测试状态端点: ${traceId}`);
    
    const response = await fetch(`/api/state/${traceId}`);
    if (response.ok) {
      const data = await response.json();
      console.log('✅ 状态获取成功:', data);
      return data;
    } else {
      console.error('❌ 状态获取失败:', response.status);
      return null;
    }
  } catch (error) {
    console.error('❌ 状态测试失败:', error);
    return null;
  }
}; 