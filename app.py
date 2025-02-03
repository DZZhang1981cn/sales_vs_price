import streamlit as st
import pandas as pd
import plotly.graph_objects as go

# 设置页面配置
st.set_page_config(
    page_title="米其林销售分析系统",
    page_icon="📊",
    layout="wide"
)

# 设置页面样式
st.markdown("""
    <style>
    .stDataFrame {
        font-size: 14px;
    }
    .css-1v0mbdj.etr89bj1 {
        margin-top: -75px;
    }
    </style>
""", unsafe_allow_html=True)

# 数据加载函数
@st.cache_data
def load_data():
    try:
        # 读取数据
        price_df = pd.read_csv('price_all.csv', index_col=0)
        sales_df = pd.read_csv('sales_all.csv')
        
        # 只保留HZ办的销售数据
        sales_df = sales_df[sales_df['Office'] == 'HZ']
        
        # 重命名sales_df中的月份列以匹配price_df
        sales_df = sales_df.rename(columns={'ID_Month_Key': 'month'})
        
        # 数据清洗和转换
        price_df['净价-不含售出'] = pd.to_numeric(price_df['净价-不含售出'], errors='coerce')
        
        # 确保CAI为整数格式
        price_df['CAI'] = pd.to_numeric(price_df['CAI'], errors='coerce').fillna(0).astype(int).astype(str)
        sales_df['Cai'] = pd.to_numeric(sales_df['Cai'], errors='coerce').fillna(0).astype(int).astype(str)
        
        # 确保month列只包含有效的年月格式（YYYYMM）
        def clean_month(x):
            try:
                # 如果是数字格式，直接转换为字符串
                if pd.api.types.is_numeric_dtype(type(x)):
                    return f"{int(x):06d}"
                # 如果是字符串，提取数字部分
                else:
                    import re
                    numbers = re.findall(r'\d+', str(x))
                    if numbers:
                        return f"{int(numbers[0]):06d}"
                    return None
            except:
                return None
        
        # 清理月份数据
        price_df['month'] = price_df['month'].apply(clean_month)
        sales_df['month'] = sales_df['month'].apply(clean_month)
        
        # 删除无效的月份数据
        price_df = price_df.dropna(subset=['month'])
        sales_df = sales_df.dropna(subset=['month'])
        
        # 转换其他列的数据类型
        price_df['规格'] = price_df['规格'].astype(str)
        
        # 计算销售额
        sales_df['销售额'] = sales_df['Shipped_Qty'] * 1
        
        # 使用规格和CAI列进行分组计算价格变化
        price_df = price_df.sort_values(['month', '规格', 'CAI'])
        price_df['上月价格'] = price_df.groupby(['规格', 'CAI'])['净价-不含售出'].shift(1)
        price_df['价格变化'] = price_df['净价-不含售出'] - price_df['上月价格']
        
        return price_df, sales_df
    except Exception as e:
        st.error(f"数据加载过程中出现错误: {str(e)}")
        if 'price_df' in locals():
            st.write("price_df列名:", price_df.columns.tolist())
            st.write("price_df month示例:", price_df['month'].head())
            st.write("price_df CAI示例:", price_df['CAI'].head())
        if 'sales_df' in locals():
            st.write("sales_df列名:", sales_df.columns.tolist())
            st.write("sales_df month示例:", sales_df['month'].head())
            st.write("sales_df Cai示例:", sales_df['Cai'].head())
        raise e

def create_trend_chart(price_df, sales_df, selected_cai=None):
    try:
        fig = go.Figure()
        
        # 准备标题信息
        if selected_cai and selected_cai != '所有':
            # 获取选中CAI的产品描述和规格
            products_info = price_df[price_df['CAI'] == selected_cai][['产品描述', '规格']].drop_duplicates()
            info_list = []
            for _, row in products_info.iterrows():
                info_list.append(f"{row['产品描述']} ({row['规格']})")
            products_str = '\n'.join(info_list)
            title_suffix = f"\nCAI: {selected_cai}\n{products_str}"
            
            # 计算平均价格和总销量
            avg_price = price_df[price_df['CAI'] == selected_cai]['净价-不含售出'].mean()
            total_sales = sales_df[sales_df['Cai'].astype(str) == selected_cai]['Shipped_Qty'].sum()
            stats_str = f"\n平均价格: {avg_price:.2f} | 总销量: {int(total_sales)}"
            title_suffix += stats_str
        else:
            title_suffix = "\n显示所有产品"
        
        # 如果选择了特定CAI，则过滤数据
        if selected_cai and selected_cai != '所有':
            price_df = price_df[price_df['CAI'] == selected_cai]
            sales_df = sales_df[sales_df['Cai'].astype(str) == selected_cai]
        
        # 准备销售数据
        sales_summary = sales_df.groupby('month')['Shipped_Qty'].sum().reset_index()
        sales_summary = sales_summary.sort_values('month')
        
        # 准备价格数据
        price_summary = price_df.groupby('month')['净价-不含售出'].mean().reset_index()
        price_summary = price_summary.sort_values('month')
        
        if not price_summary.empty and not sales_summary.empty:
            # 创建月份序列
            all_months = sorted(set(price_summary['month'].tolist() + sales_summary['month'].tolist()))
            
            # 确保所有月份都存在，没有数据的填充为0
            full_sales = pd.DataFrame({'month': all_months})
            full_sales = full_sales.merge(sales_summary, on='month', how='left').fillna(0)
            
            full_prices = pd.DataFrame({'month': all_months})
            full_prices = full_prices.merge(price_summary, on='month', how='left')
            
            # 处理销售数量的显示文本
            sales_text = full_sales['Shipped_Qty'].fillna(0).round(0).astype(int)
            sales_text = sales_text.apply(lambda x: '' if x == 0 else str(x))
            
            # 处理价格的显示文本
            price_text = full_prices['净价-不含售出'].fillna(0).round(0).astype(int)
            price_text = price_text.apply(lambda x: '' if x == 0 else str(x))
            
            # 添加柱状图
            fig.add_trace(go.Bar(
                x=[f"{x[:4]}/{x[4:]}" for x in full_sales['month']],
                y=full_sales['Shipped_Qty'],
                name='销售数量',
                marker_color='rgb(33, 150, 243)',
                text=sales_text,
                textposition='outside',
                textfont=dict(size=10),
            ))
            
            # 添加折线图
            fig.add_trace(go.Scatter(
                x=[f"{x[:4]}/{x[4:]}" for x in full_prices['month']],
                y=full_prices['净价-不含售出'],
                name='平均价格',
                mode='lines+markers+text',
                line=dict(color='rgb(255, 82, 82)', width=2),
                marker=dict(size=8),
                text=price_text,
                textposition='top center',
                textfont=dict(color='rgb(255, 82, 82)', size=10),
                yaxis='y2'
            ))
        
        # 更新布局
        fig.update_layout(
            title=dict(
                text=f"价格和销售趋势{title_suffix}",
                x=0.5,
                xanchor='center',
                font=dict(size=14)
            ),
            height=600,  # 增加高度以适应更长的标题
            margin=dict(l=50, r=50, t=150, b=50),  # 增加上边距以容纳更长的标题
            xaxis=dict(
                title="月份",
                tickangle=45,
                showgrid=True,
                gridcolor='rgba(128, 128, 128, 0.2)',
                tickfont=dict(size=10),
                dtick=1
            ),
            yaxis=dict(
                title="销售数量",
                titlefont=dict(color='rgb(33, 150, 243)'),
                tickfont=dict(color='rgb(33, 150, 243)', size=10),
                showgrid=True,
                gridcolor='rgba(128, 128, 128, 0.2)',
                zeroline=False
            ),
            yaxis2=dict(
                title="平均价格",
                titlefont=dict(color='rgb(255, 82, 82)'),
                tickfont=dict(color='rgb(255, 82, 82)', size=10),
                overlaying='y',
                side='right',
                showgrid=False,
                zeroline=False
            ),
            showlegend=True,
            legend=dict(
                orientation="h",
                yanchor="bottom",
                y=1.02,
                xanchor="right",
                x=1,
                font=dict(size=10)
            ),
            plot_bgcolor='rgb(25, 25, 25)',
            paper_bgcolor='rgb(25, 25, 25)',
            font=dict(color='white')
        )
        
        return fig
    except Exception as e:
        st.error(f"创建趋势图时出现错误: {str(e)}")
        st.write("错误详情：", e)
        if 'price_summary' in locals():
            st.write("price_summary示例:", price_summary.head())
        if 'sales_summary' in locals():
            st.write("sales_summary示例:", sales_summary.head())
        raise e

try:
    # 加载数据
    price_df, sales_df = load_data()
    
    # 过滤数据，只显示从2024年1月开始的数据
    price_df = price_df[price_df['month'].astype(str) >= '202401']
    sales_df = sales_df[sales_df['month'].astype(str) >= '202401']
    
    # 创建会话状态来存储选中的CAI
    if 'selected_cai' not in st.session_state:
        st.session_state.selected_cai = '所有'
    
    # 创建筛选器
    st.markdown("### 数据筛选")
    filter_cols = st.columns(3)
    
    with filter_cols[0]:
        all_cais = ['所有'] + sorted(price_df['CAI'].unique().tolist())
        selected_cai = st.selectbox(
            '选择CAI',
            all_cais,
            index=all_cais.index(st.session_state.selected_cai),
            key='cai_selector_main',
            help="支持搜索，直接输入CAI或产品描述关键字",
            placeholder="输入CAI或产品描述搜索..."
        )
        st.session_state.selected_cai = selected_cai
    
    with filter_cols[1]:
        all_dims = ['所有'] + sorted(price_df['规格'].unique().tolist())
        selected_dim = st.selectbox(
            '选择规格',
            all_dims,
            key='dim_selector',
            help="支持搜索，直接输入规格关键字",
            placeholder="输入规格搜索..."
        )
    
    with filter_cols[2]:
        all_months = ['所有'] + sorted(price_df['month'].unique().tolist())
        # 将月份格式化为YYYY/MM格式用于显示
        month_display = ['所有'] + [f"{x[:4]}/{x[4:]}" for x in all_months[1:]]
        month_dict = dict(zip(month_display[1:], all_months[1:]))
        selected_month_display = st.selectbox(
            '选择月份',
            month_display,
            key='month_selector',
            help="支持搜索，直接输入年份或月份",
            placeholder="输入年份或月份搜索..."
        )
        # 将显示格式转换回实际的月份值
        selected_month = month_dict[selected_month_display] if selected_month_display != '所有' else '所有'
    
    # 根据筛选条件过滤数据
    filtered_price_df = price_df.copy()
    filtered_sales_df = sales_df.copy()
    
    if selected_cai != '所有':
        filtered_price_df = filtered_price_df[filtered_price_df['CAI'] == selected_cai]
        filtered_sales_df = filtered_sales_df[filtered_sales_df['Cai'].astype(str) == selected_cai]
    
    if selected_dim != '所有':
        filtered_price_df = filtered_price_df[filtered_price_df['规格'] == selected_dim]
    
    if selected_month != '所有':
        filtered_price_df = filtered_price_df[filtered_price_df['month'] == selected_month]
        filtered_sales_df = filtered_sales_df[filtered_sales_df['month'] == selected_month]
    
    # 创建主数据表格
    st.markdown("### 价格明细")
    
    # 合并价格和销售数据
    merged_df = pd.merge(
        filtered_price_df,
        filtered_sales_df[['month', 'Cai', 'Shipped_Qty']],
        left_on=['month', 'CAI'],
        right_on=['month', 'Cai'],
        how='left'
    ).drop('Cai', axis=1)
    
    # 格式化月份显示
    merged_df['显示月份'] = merged_df['month'].apply(lambda x: f"{x[:4]}/{x[4:]}")
    
    # 选择要显示的列并重新排序
    columns_to_display = ['显示月份', '规格', 'CAI', '产品描述', '净价-不含售出', '上月价格', '价格变化', 'Shipped_Qty']
    formatted_df = merged_df[columns_to_display].copy()
    
    # 重命名列
    formatted_df = formatted_df.rename(columns={
        '显示月份': '月份',
        'Shipped_Qty': '销售数量'
    })
    
    # 处理数值格式
    formatted_df['销售数量'] = formatted_df['销售数量'].fillna(0).astype(int)
    formatted_df = formatted_df.round(2)
    
    # 按月份降序排序
    formatted_df = formatted_df.sort_values('月份', ascending=False)
    
    st.dataframe(
        formatted_df,
        hide_index=True,
        use_container_width=True
    )
    
    # 创建趋势图
    st.markdown("### 价格和销售趋势")
    fig = create_trend_chart(filtered_price_df, filtered_sales_df, selected_cai)
    st.plotly_chart(fig, use_container_width=True)
    
    # 创建统计分析
    st.markdown("### 价格统计")
    stats_cols = st.columns(2)
    
    with stats_cols[0]:
        # 按规格统计
        dim_stats = filtered_price_df.groupby('规格')['净价-不含售出'].agg(['mean', 'min', 'max']).round(2)
        dim_stats.columns = ['平均价格', '最低价格', '最高价格']
        st.write("按规格统计")
        st.dataframe(dim_stats)
    
    with stats_cols[1]:
        # 按CAI统计
        latest_prices = filtered_price_df.sort_values('month').groupby(['CAI', '产品描述'])['净价-不含售出'].last()
        cai_stats = filtered_price_df.groupby(['CAI', '产品描述']).agg(
            平均价格=('净价-不含售出', 'mean'),
            最低价格=('净价-不含售出', 'min'),
            最高价格=('净价-不含售出', 'max')
        ).round(2)
        cai_stats['最近价格'] = latest_prices
        cai_stats = cai_stats.reset_index()
        st.write("按CAI统计")
        
        # 显示CAI统计表格
        st.dataframe(
            cai_stats,
            hide_index=True,
            use_container_width=True
        )
        
        # 添加一个选择器来选择CAI
        st.write("选择CAI查看趋势")
        selected_cai_from_stats = st.selectbox(
            "选择CAI",
            ['所有'] + sorted(cai_stats['CAI'].unique().tolist()),
            key='cai_selector_from_stats',
            help="支持搜索，直接输入CAI或产品描述关键字",
            placeholder="输入CAI或产品描述搜索..."
        )
        
        if selected_cai_from_stats != st.session_state.selected_cai:
            st.session_state.selected_cai = selected_cai_from_stats
            st.experimental_rerun()

except Exception as e:
    st.error(f"数据处理过程中出现错误: {str(e)}")
    st.write("错误详情：", e)
    st.write("price_df 列名:", price_df.columns.tolist() if 'price_df' in locals() else "price_df not loaded")
    st.write("sales_df 列名:", sales_df.columns.tolist() if 'sales_df' in locals() else "sales_df not loaded")
