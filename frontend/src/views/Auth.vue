<template>
  <div class="auth-container">
    <div class="auth-box">
      <h2>{{ isLogin ? '登录' : '注册' }}</h2>
      <el-form 
        :model="form"
        :rules="rules"
        ref="authForm"
        label-width="0"
        class="auth-form"
      >
        <el-form-item prop="username">
          <el-input 
            v-model="form.username"
            placeholder="用户名"
            :prefix-icon="User"
          />
        </el-form-item>
        <el-form-item prop="password">
          <el-input 
            v-model="form.password"
            type="password"
            placeholder="密码"
            :prefix-icon="Lock"
            show-password
          />
        </el-form-item>
        <el-form-item prop="confirmPassword" v-if="!isLogin">
          <el-input 
            v-model="form.confirmPassword"
            type="password"
            placeholder="确认密码"
            :prefix-icon="Lock"
            show-password
          />
        </el-form-item>
        <el-form-item>
          <el-button type="primary" @click="handleSubmit" :loading="loading" class="submit-btn">
            {{ isLogin ? '登录' : '注册' }}
          </el-button>
        </el-form-item>
      </el-form>
      <div class="auth-footer">
        <a href="javascript:void(0)" @click="toggleAuthMode">
          {{ isLogin ? '没有账号？立即注册' : '已有账号？立即登录' }}
        </a>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, reactive, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { User, Lock } from '@element-plus/icons-vue'

const router = useRouter()
const authForm = ref(null)
const isLogin = ref(true)
const loading = ref(false)

// 组件加载时检查登录状态
onMounted(() => {
  // 确保用户已完全退出
  const currentUser = localStorage.getItem('currentUser')
  if (currentUser) {
    localStorage.removeItem('currentUser')
    router.push('/auth')
  }
})

const form = reactive({
  username: '',
  password: '',
  confirmPassword: ''
})

const rules = reactive({
  username: [
    { required: true, message: '请输入用户名', trigger: 'blur' },
    { min: 3, max: 20, message: '用户名长度应为3-20个字符', trigger: 'blur' }
  ],
  password: [
    { required: true, message: '请输入密码', trigger: 'blur' },
    { min: 6, message: '密码长度应至少为6个字符', trigger: 'blur' }
  ],
  confirmPassword: [
    {
      validator: (rule, value, callback) => {
        if (!isLogin.value) {
          if (value === '') {
            callback(new Error('请确认密码'))
          } else if (value !== form.password) {
            callback(new Error('两次输入密码不一致'))
          } else {
            callback()
          }
        } else {
          callback()
        }
      },
      trigger: 'blur'
    }
  ]
})

const handleSubmit = async () => {
  if (!authForm.value) return
  
  try {
    await authForm.value.validate()
    loading.value = true

    if (isLogin.value) {
      // 登录逻辑
      const storedUser = localStorage.getItem(`user_${form.username}`)
      if (!storedUser) {
        ElMessage.error('用户不存在')
        return
      }

      const userData = JSON.parse(storedUser)
      if (userData.password !== form.password) {
        ElMessage.error('密码错误')
        return
      }

      // 登录成功
      localStorage.setItem('currentUser', form.username)
      ElMessage.success('登录成功')
      router.push('/')
    } else {
      // 注册逻辑
      const existingUser = localStorage.getItem(`user_${form.username}`)
      if (existingUser) {
        ElMessage.error('用户名已存在')
        return
      }

      // 保存用户信息
      localStorage.setItem(`user_${form.username}`, JSON.stringify({
        username: form.username,
        password: form.password,
        registeredAt: Date.now()
      }))

      ElMessage.success('注册成功，请登录')
      isLogin.value = true
      form.password = ''
      form.confirmPassword = ''
    }
  } catch (error) {
    console.error('表单验证失败:', error)
  } finally {
    loading.value = false
  }
}

const toggleAuthMode = () => {
  isLogin.value = !isLogin.value
  form.password = ''
  form.confirmPassword = ''
  if (authForm.value) {
    authForm.value.clearValidate()
  }
}
</script>

<style scoped>
.auth-container {
  display: flex;
  justify-content: center;
  align-items: center;
  min-height: 100vh;
  background-color: #f5f7fa;
}

.auth-box {
  width: 100%;
  max-width: 400px;
  padding: 40px;
  background: #fff;
  border-radius: 8px;
  box-shadow: 0 2px 12px 0 rgba(0, 0, 0, 0.1);
}

.auth-box h2 {
  text-align: center;
  margin-bottom: 30px;
  color: #303133;
}

.auth-form {
  margin-bottom: 20px;
}

.submit-btn {
  width: 100%;
  margin-top: 10px;
}

.auth-footer {
  text-align: center;
}

.auth-footer a {
  color: #409EFF;
  text-decoration: none;
}

.auth-footer a:hover {
  text-decoration: underline;
}
</style>
