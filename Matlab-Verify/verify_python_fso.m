%% =========================================================================
%  FSO无线光通信系统 — Python项目图表验证脚本 (MATLAB)
%  对标: PyQt5 + Matplotlib 可视化平台 (plot_widgets.py 8张图表)
%  默认参数: 晴天场景 (parameter_panel.py reset_params)
%% =========================================================================
clear; clc; close all;

fprintf('============================================================\n');
fprintf('  FSO 链路特性 MATLAB 验证脚本\n');
fprintf('  对标 Python 项目 8 张数据图表\n');
fprintf('  默认场景: 晴天 (V=23km, Cn2=1e-15)\n');
fprintf('============================================================\n\n');

%% ── 全局物理常数 ─────────────────────────────────────────────────────────
K_B   = 1.380649e-23;       % 玻尔兹曼常数 (J/K)
Q_E   = 1.602176634e-19;    % 元电荷 (C)
C     = 2.99792458e8;       % 光速 (m/s)
PI    = pi;

%% ── Python项目默认参数 (晴天场景) ───────────────────────────────────────
% 系统参数
lambda_nm   = 1550;         % 波长 (nm)
lambda_m    = lambda_nm * 1e-9;
power_mw    = 25.0;         % 发射功率 (mW)
P_T_w       = power_mw * 1e-3;  % 转换为 W
P_T_dbm     = 10*log10(P_T_w * 1000);
D_T_m       = 0.025;        % 发射口径 (m) = 2.5 cm
D_R_m       = 0.08;         % 接收口径 (m) = 8 cm
theta_div   = 2e-3;         % 光束发散全角 (rad) = 2 mrad
jitter_urad = 0.0;          % 指向抖动 (μrad)
jitter_rad  = jitter_urad * 1e-6;
mu_T        = 0.8;          % 发射光学效率
mu_R        = 0.8;          % 接收光学效率
modulation  = 'OOK';        % 调制方式
M_ppm       = 4;            % PPM阶数 (默认4)
data_rate   = 155e6;        % 数据速率 155 Mb/s

% 信道参数
distance_km = 1.0;          % 传输距离 (km)
distance_m  = distance_km * 1000;
visibility  = 23.0;         % 能见度 (km)
Cn2         = 1.0e-15;      % 大气折射率结构常数
rainfall    = 0.0;          % 降雨量 (mm/h)
snowfall    = 0.0;          % 降雪量 (mm/h)
snow_type   = 'wet';        % 湿雪

% 探测器参数 (PIN默认)
detector    = 'PIN';
R_p         = 0.5;          % 响应度 (A/W)
R_L         = 50;           % 负载电阻 (Ω)
T_K         = 300;          % 噪声温度 (K)
P_B_w       = 0.0;          % 背景光功率 (W)
sensitivity = -30;          % 接收灵敏度 (dBm)

% APD参数 (备用)
M_apd       = 50;
F_apd       = 3.0;

%% ── 辅助函数定义 (嵌套函数替代) ─────────────────────────────────────────
% Kim模型p值
kim_p = @(V) (V > 50) .* 1.6 + ...
             (V > 6 & V <= 50) .* 1.3 + ...
             (V > 1 & V <= 6) .* (0.16*V + 0.34) + ...
             (V > 0.5 & V <= 1) .* (V - 0.5) + ...
             (V <= 0.5) .* 0.0;

% 消光系数 (Naperian km^-1)
attenuation_coeff = @(V, lambda_nm) (3.91 ./ V) .* (lambda_nm / 550).^(-kim_p(V));

% 雨衰 (dB/km)
rain_atten = @(R) 1.076 * R.^0.67;

% 雪衰 (dB/km)
snow_atten = @(S, type) (strcmp(type,'dry') .* (5.42e-5 * S.^1.38 + 5.50) + ...
                         strcmp(type,'wet') .* (1.023e-4 * S.^3.79 + 0.23));

% 总信道衰减 (dB)
total_channel_loss = @(V, L_km, lambda_nm, rain, snow, stype) ...
    4.343 * attenuation_coeff(V, lambda_nm) .* L_km + ...
    rain_atten(rain) .* L_km + ...
    snow_atten(snow, stype) .* L_km;

% 光束直径
beam_diameter = @(D_T, theta, L) D_T + theta .* L;

% 几何损耗 (线性)
geo_loss = @(D_R, D_beam) min((D_R ./ D_beam).^2, 1);

% 几何损耗 (dB)
geo_loss_db = @(D_R, D_beam) 10*log10(geo_loss(D_R, D_beam));

% 指向误差损耗 (简化模型)
pointing_loss = @(sigma_s, theta_div) exp(-2 * (sigma_s ./ theta_div).^2);

% 接收功率 (W)
received_power = @(P_T, tau_atm, L_geo, L_point, eta_T, eta_R) ...
    P_T .* tau_atm .* L_geo .* L_point .* eta_T .* eta_R;

% 带宽
bandwidth = @(Rb, mod, M) (strcmp(mod,'OOK')|strcmp(mod,'SIM')) .* Rb + ...
                          strcmp(mod,'PPM') .* M .* Rb ./ log2(M);

% 热噪声
noise_thermal = @(T, B, R_L) 4 * K_B .* T .* B ./ R_L;

% 散粒噪声
noise_shot = @(R_p, P_R, P_B, B) 2 .* Q_E .* R_p .* (P_R + P_B) .* B;

% PIN SNR
snr_pin = @(P_R, R_p, m, T, B, R_L, P_B) ...
    0.5 .* m.^2 .* (R_p .* P_R).^2 ./ (noise_thermal(T,B,R_L) + noise_shot(R_p,P_R,P_B,B));

% Rytov方差
rytov_var = @(Cn2, lambda_m, L_m) 1.23 .* Cn2 .* (2*PI./lambda_m).^(7/6) .* L_m.^(11/6);

% 闪烁指数 (全范围平面波)
scint_index = @(sigma_R2) ...
    exp(0.49.*sigma_R2./(1+1.11.*sigma_R2.^(12/5)).^(7/6) + ...
        0.51.*sigma_R2./(1+0.69.*sigma_R2.^(12/5)).^(5/6)) - 1;

% BER函数
ber_ook = @(snr) 0.5 .* erfc(sqrt(snr/2));
ber_ppm = @(snr, M) (M/2)/(M-1) .* 0.5 .* erfc(sqrt(snr .* M .* log2(M) / 4));
ber_sim = @(snr) 0.5 .* erfc(sqrt(snr));

%% =======================================================================
%  计算当前工作点数值结果 (与Python仿真引擎一致)
%% =======================================================================

% --- 1. 大气衰减 ---
sigma_atm = attenuation_coeff(visibility, lambda_nm);
atm_loss_db = total_channel_loss(visibility, distance_km, lambda_nm, rainfall, snowfall, snow_type);
tau_atm = 10^(-atm_loss_db / 10);

% --- 2. 几何损耗 ---
D_beam_now = beam_diameter(D_T_m, theta_div, distance_m);
L_geo_now = geo_loss(D_R_m, D_beam_now);
L_geo_dB_now = geo_loss_db(D_R_m, D_beam_now);
L_point_now = pointing_loss(jitter_rad, theta_div);
L_point_dB = -10*log10(L_point_now);

% --- 3. 接收功率 ---
P_R_w = received_power(P_T_w, tau_atm, L_geo_now, L_point_now, mu_T, mu_R);
P_R_dbm = 10*log10(P_R_w * 1000);
opt_loss_db = -10*log10(mu_T * mu_R);
total_loss_db = atm_loss_db + abs(L_geo_dB_now) + opt_loss_db + L_point_dB;

% --- 4. SNR ---
B = bandwidth(data_rate, modulation, M_ppm);
n_th = noise_thermal(T_K, B, R_L);
n_sh = noise_shot(R_p, P_R_w, P_B_w, B);
snr = snr_pin(P_R_w, R_p, 1.0, T_K, B, R_L, P_B_w);
snr_db = 10*log10(snr);

% --- 5. 湍流 ---
sigma_R2 = rytov_var(Cn2, lambda_m, distance_m);
sigma_I2 = scint_index(sigma_R2);
if sigma_R2 < 1, regime = '弱湍流';
elseif sigma_R2 <= 25, regime = '中强湍流';
else, regime = '饱和湍流'; end

% --- 6. BER (当前工作点) ---
ber_ook_awgn = ber_ook(snr);
ber_ppm_awgn = ber_ppm(snr, M_ppm);
ber_sim_awgn = ber_sim(snr);

% 湍流BER (弱湍流: 对数正态, Gauss-Hermite求积)
if sigma_R2 > 0
    sigma_l = sqrt(sigma_R2);
    num_pts = 50;
    [x_nodes, weights] = hermite_gauss(num_pts);
    I_vals = exp(sqrt(2)*sigma_l*x_nodes - sigma_R2/2);
    ber_ook_turb = sum(weights .* ber_ook(snr .* I_vals)) / sqrt(PI);
    ber_ppm_turb = sum(weights .* ber_ppm(snr .* I_vals, M_ppm)) / sqrt(PI);
    ber_sim_turb = sum(weights .* ber_sim(snr .* I_vals)) / sqrt(PI);
else
    ber_ook_turb = ber_ook_awgn;
    ber_ppm_turb = ber_ppm_awgn;
    ber_sim_turb = ber_sim_awgn;
end

% 链路余量
margin = P_R_dbm - sensitivity;

fprintf('【当前工作点计算结果】\n');
fprintf('  波长 = %d nm, 距离 = %.2f km, 能见度 = %.1f km\n', lambda_nm, distance_km, visibility);
fprintf('  大气衰减 = %.4f dB, 几何损耗 = %.2f dB\n', atm_loss_db, L_geo_dB_now);
fprintf('  接收功率 = %.2f dBm, SNR = %.2f dB\n', P_R_dbm, snr_db);
fprintf('  Rytov方差 = %.6f, 闪烁指数 = %.6f (%s)\n', sigma_R2, sigma_I2, regime);
fprintf('  OOK BER (AWGN) = %.4e, (湍流) = %.4e\n', ber_ook_awgn, ber_ook_turb);
fprintf('  链路余量 = %.2f dB\n\n', margin);

%% =======================================================================
%  生成曲线数据 (与Python simulation_worker.py一致)
%% =======================================================================

% 距离范围: linspace(0.01, max(distance_km*2, 5), 200)
dist_range = linspace(0.01, max(distance_km*2, 5), 200);
dist_range_m = dist_range * 1000;

% SNR范围: linspace(0, 40, 200)
snr_db_range = linspace(0, 40, 200);
snr_lin_range = 10.^(snr_db_range/10);

% I范围: linspace(0.01, 6, 500)
I_range = linspace(0.01, 6, 500);

% --- 大气衰减曲线 ---
sigma_kim = attenuation_coeff(visibility, lambda_nm);
rain_per_km = rain_atten(rainfall);
snow_per_km = snow_atten(snowfall, snow_type);
loss_per_km = 4.343 * sigma_kim + rain_per_km + snow_per_km;
atm_loss_curve = loss_per_km .* dist_range;

% --- 闪烁指数曲线 ---
sigma_R2_curve = rytov_var(Cn2, lambda_m, dist_range_m);
sigma_I2_curve = scint_index(sigma_R2_curve);

% --- 接收功率曲线 ---
tau_curve = 10.^(-loss_per_km .* dist_range / 10);
D_beam_curve = D_T_m + theta_div .* dist_range_m;
L_geo_curve = min((D_R_m ./ D_beam_curve).^2, 1);
P_R_curve_w = P_T_w .* tau_curve .* L_geo_curve .* L_point_now .* mu_T .* mu_R;
P_R_curve_dbm = 10.*log10(P_R_curve_w .* 1000);
P_R_curve_dbm(P_R_curve_w <= 0) = -100;

% --- BER曲线 (AWGN) ---
ber_ook_curve = ber_ook(snr_lin_range);
ber_ppm_curve = ber_ppm(snr_lin_range, M_ppm);
ber_sim_curve = ber_sim(snr_lin_range);

% --- BER曲线 (湍流) ---
% 逐点计算 (MATLAB向量化处理Gauss-Hermite)
ber_ook_turb_curve = zeros(size(snr_lin_range));
ber_ppm_turb_curve = zeros(size(snr_lin_range));
ber_sim_turb_curve = zeros(size(snr_lin_range));

if sigma_R2 > 0
    sigma_l = sqrt(sigma_R2);
    [x_nodes, weights] = hermite_gauss(50);
    I_vals = exp(sqrt(2)*sigma_l*x_nodes - sigma_R2/2);
    for i = 1:length(snr_lin_range)
        s = snr_lin_range(i);
        ber_ook_turb_curve(i) = sum(weights(:) .* ber_ook(s .* I_vals(:))) / sqrt(PI);
        ber_ppm_turb_curve(i) = sum(weights(:) .* ber_ppm(s .* I_vals(:), M_ppm)) / sqrt(PI);
        ber_sim_turb_curve(i) = sum(weights(:) .* ber_sim(s .* I_vals(:))) / sqrt(PI);
    end
else
    ber_ook_turb_curve = ber_ook_curve;
    ber_ppm_turb_curve = ber_ppm_curve;
    ber_sim_turb_curve = ber_sim_curve;
end

% --- 概率分布曲线 ---
% 对数正态 (使用max(sigma_R2, 0.05)与Python一致)
sigma_R2_pdf = max(sigma_R2, 0.05);
pdf_ln = (1./(I_range*sqrt(2*PI*sigma_R2_pdf))) .* ...
         exp(-((log(I_range) + sigma_R2_pdf/2).^2)/(2*sigma_R2_pdf));

% Gamma-Gamma
if sigma_R2 > 0.01
    slx2_gg = 0.49*sigma_R2 / (1 + 1.11*sigma_R2^(12/5))^(7/6);
    sly2_gg = 0.51*sigma_R2 / (1 + 0.69*sigma_R2^(12/5))^(5/6);
    alpha_gg = 1 / (exp(slx2_gg) - 1);
    beta_gg = 1 / (exp(sly2_gg) - 1);
    ab = alpha_gg * beta_gg;
    ab_sum_half = (alpha_gg + beta_gg)/2;
    order_gg = alpha_gg - beta_gg;
    
    % 使用对数运算避免溢出
    ln_coeff = log(2) + ab_sum_half*log(ab) - gammaln(alpha_gg) - gammaln(beta_gg);
    ln_I_power = (ab_sum_half - 1) .* log(I_range);
    arg = 2 .* sqrt(ab .* I_range);
    K_val = besselk(order_gg, arg);
    pdf_gg = zeros(size(I_range));
    valid = K_val > 0;
    pdf_gg(valid) = exp(ln_coeff + ln_I_power(valid) + log(K_val(valid)));
else
    pdf_gg = zeros(size(I_range));
    alpha_gg = 0; beta_gg = 0;
end

% 负指数
pdf_ne = exp(-I_range);

%% =======================================================================
%  图1: 大气衰减 vs 距离 (对应 _plot_atm)
%% =======================================================================
fig1 = figure('Name', '大气衰减 vs 距离', 'Position', [100 600 500 380], 'Color', 'w');
plot(dist_range, atm_loss_curve, 'Color', [0.082 0.396 0.753], 'LineWidth', 2, 'DisplayName', '大气衰减曲线');
hold on;
yline(atm_loss_db, '--', 'Color', [0.776 0.157 0.157], 'LineWidth', 1.2, ...
    'DisplayName', sprintf('当前: %.2f dB', atm_loss_db));
xline(distance_km, ':', 'Color', [0.776 0.157 0.157], 'HandleVisibility', 'off');
xlabel('传输距离 (km)', 'FontSize', 10);
ylabel('大气衰减 (dB)', 'FontSize', 10);
title(sprintf('大气衰减 vs 距离  (V=%.0fkm, λ=%.0fnm)', visibility, lambda_nm), ...
    'FontSize', 12, 'FontWeight', 'bold');
grid on; grid minor;
legend('Location', 'best', 'FontSize', 9);
box off;

%% =======================================================================
%  图2: 闪烁指数 vs 距离 (对应 _plot_scintillation)
%% =======================================================================
fig2 = figure('Name', '闪烁指数 vs 距离', 'Position', [620 600 500 380], 'Color', 'w');
plot(dist_range, sigma_I2_curve, 'Color', [0.902 0.318 0.0], 'LineWidth', 2, 'DisplayName', '闪烁指数曲线');
hold on;
yline(1.0, '--', 'Color', [0.329 0.431 0.478], 'LineWidth', 1, ...
    'DisplayName', '饱和值 σ_I²=1');
yline(sigma_I2, '--', 'Color', [0.082 0.396 0.753], 'LineWidth', 1.2, ...
    'DisplayName', sprintf('当前: σ_I²=%.4f', sigma_I2));
xline(distance_km, ':', 'Color', [0.082 0.396 0.753], 'HandleVisibility', 'off');
xlabel('传输距离 (km)', 'FontSize', 10);
ylabel('闪烁指数 σ_I²', 'FontSize', 10);
title(sprintf('闪烁指数 vs 距离  (Cn²=%.1e)', Cn2), ...
    'FontSize', 12, 'FontWeight', 'bold');
grid on; grid minor;
legend('Location', 'best', 'FontSize', 9);
box off;

%% =======================================================================
%  图3: 接收功率 vs 距离 (对应 _plot_power)
%% =======================================================================
fig3 = figure('Name', '接收功率 vs 距离', 'Position', [1140 600 500 380], 'Color', 'w');
plot(dist_range, P_R_curve_dbm, 'Color', [0.180 0.490 0.196], 'LineWidth', 2, 'DisplayName', '接收功率曲线');
hold on;
yline(sensitivity, '--', 'Color', [0.776 0.157 0.157], 'LineWidth', 1.2, ...
    'DisplayName', sprintf('灵敏度: %d dBm', sensitivity));
yline(P_R_dbm, '--', 'Color', [0.082 0.396 0.753], 'LineWidth', 1.2, ...
    'DisplayName', sprintf('当前: %.2f dBm', P_R_dbm));
xlabel('传输距离 (km)', 'FontSize', 10);
ylabel('接收功率 (dBm)', 'FontSize', 10);
title('接收功率 vs 距离', 'FontSize', 12, 'FontWeight', 'bold');
grid on; grid minor;
legend('Location', 'best', 'FontSize', 9);
box off;

%% =======================================================================
%  图4: 噪声分析饼图 (对应 _plot_noise)
%% =======================================================================
fig4 = figure('Name', '噪声分析', 'Position', [100 100 500 380], 'Color', 'w');
total_noise = n_th + n_sh;
sizes = [n_th/total_noise*100, n_sh/total_noise*100];
labels = {sprintf('热噪声  %.2e A² (%.1f%%)', n_th, sizes(1)), ...
          sprintf('散粒噪声  %.2e A² (%.1f%%)', n_sh, sizes(2))};
colors = [0.902 0.318 0.0; 0.082 0.396 0.753];
pie(sizes, labels);
colormap(colors);
title('噪声功率组成', 'FontSize', 12, 'FontWeight', 'bold');

%% =======================================================================
%  图5: BER vs SNR — AWGN信道 (对应 _plot_ber_awgn)
%% =======================================================================
fig5 = figure('Name', 'BER vs SNR (AWGN)', 'Position', [620 100 500 380], 'Color', 'w');
semilogy(snr_db_range, ber_ook_curve, 'Color', [0.082 0.396 0.753], 'LineWidth', 2, 'DisplayName', 'OOK');
hold on;
semilogy(snr_db_range, ber_ppm_curve, 'Color', [0.902 0.318 0.0], 'LineWidth', 2, 'DisplayName', sprintf('%d-PPM', M_ppm));
semilogy(snr_db_range, ber_sim_curve, 'Color', [0.180 0.490 0.196], 'LineWidth', 2, 'DisplayName', 'SIM-BPSK');
if snr_db > 0
    xline(snr_db, ':', 'Color', [0.329 0.431 0.478], ...
        'DisplayName', sprintf('当前 SNR=%.1f dB', snr_db));
end
yline(1e-9, '--', 'Color', [0.329 0.431 0.478], 'LineWidth', 1, 'HandleVisibility', 'off');
text(1, 1.5e-9, 'BER=10^{-9}', 'FontSize', 9, 'Color', [0.329 0.431 0.478]);
xlabel('SNR (dB)', 'FontSize', 10);
ylabel('误码率 (BER)', 'FontSize', 10);
title('BER vs SNR — AWGN 信道 (无湍流)', 'FontSize', 12, 'FontWeight', 'bold');
ylim([1e-15 1]); xlim([0 40]);
grid on; grid minor;
legend('Location', 'best', 'FontSize', 9);
box off;

%% =======================================================================
%  图6: BER vs SNR — 湍流信道 (对应 _plot_ber_turbulence)
%% =======================================================================
fig6 = figure('Name', 'BER vs SNR (湍流)', 'Position', [1140 100 500 380], 'Color', 'w');
% AWGN参考 (虚线)
semilogy(snr_db_range, ber_ook_curve, '--', 'Color', [0.082 0.396 0.753], ...
    'LineWidth', 1.2, 'DisplayName', 'OOK (AWGN参考)');
hold on;
semilogy(snr_db_range, ber_ppm_curve, '--', 'Color', [0.902 0.318 0.0], ...
    'LineWidth', 1.2, 'DisplayName', sprintf('%d-PPM (AWGN参考)', M_ppm));
semilogy(snr_db_range, ber_sim_curve, '--', 'Color', [0.180 0.490 0.196], ...
    'LineWidth', 1.2, 'DisplayName', 'SIM-BPSK (AWGN参考)');
% 湍流实线
semilogy(snr_db_range, ber_ook_turb_curve, 'Color', [0.082 0.396 0.753], ...
    'LineWidth', 2, 'DisplayName', sprintf('OOK  (σ_R²=%.3f)', sigma_R2));
semilogy(snr_db_range, ber_ppm_turb_curve, 'Color', [0.902 0.318 0.0], ...
    'LineWidth', 2, 'DisplayName', sprintf('%d-PPM (σ_R²=%.3f)', M_ppm, sigma_R2));
semilogy(snr_db_range, ber_sim_turb_curve, 'Color', [0.180 0.490 0.196], ...
    'LineWidth', 2, 'DisplayName', sprintf('SIM  (σ_R²=%.3f)', sigma_R2));
if snr_db > 0
    xline(snr_db, ':', 'Color', [0.329 0.431 0.478], 'HandleVisibility', 'off');
end
yline(1e-9, '--', 'Color', [0.329 0.431 0.478], 'LineWidth', 1, 'HandleVisibility', 'off');
xlabel('SNR (dB)', 'FontSize', 10);
ylabel('误码率 (BER)', 'FontSize', 10);
title(sprintf('BER vs SNR — 湍流信道 (%s)', regime), 'FontSize', 12, 'FontWeight', 'bold');
ylim([1e-12 1]); xlim([0 40]);
grid on; grid minor;
legend('Location', 'southwest', 'FontSize', 9);
box off;

%% =======================================================================
%  图7: 光强概率密度分布 (对应 _plot_distributions)
%% =======================================================================
fig7 = figure('Name', '光强概率密度分布', 'Position', [100 -300 700 420], 'Color', 'w');
plot(I_range, pdf_ln, 'Color', [0.082 0.396 0.753], 'LineWidth', 2, ...
    'DisplayName', sprintf('对数正态 (弱湍流, σ_R²=%.3f)', max(sigma_R2, 0.05)));
hold on;
if any(pdf_gg > 0)
    plot(I_range, pdf_gg, 'Color', [0.902 0.318 0.0], 'LineWidth', 2, ...
        'DisplayName', sprintf('Gamma-Gamma (α=%.2f, β=%.2f)', alpha_gg, beta_gg));
end
plot(I_range, pdf_ne, 'Color', [0.180 0.490 0.196], 'LineWidth', 2, ...
    'DisplayName', '负指数 (饱和湍流)');
xlabel('归一化光强 I/\langleI\rangle', 'FontSize', 10);
ylabel('概率密度 f(I)', 'FontSize', 10);
title(sprintf('接收光强概率密度分布 — 当前: %s', regime), 'FontSize', 12, 'FontWeight', 'bold');
xlim([0 5]);
grid on; grid minor;
legend('Location', 'best', 'FontSize', 9);
box off;

%% =======================================================================
%  图8: 链路预算瀑布图 (对应 _plot_waterfall)
%% =======================================================================
fig8 = figure('Name', '链路预算瀑布图', 'Position', [840 -300 700 420], 'Color', 'w');

% 收集数据
P_T_dbm = 10*log10(P_T_w * 1000);
opt_db = opt_loss_db;
pnt_db = L_point_dB;

labels = {'发射功率\nP_T', '大气\n衰减', '几何\n损耗', '光学\n损耗', '指向误差', '接收功率\nP_R'};
legend_labels = {'发射功率 P_T', '大气衰减', '几何损耗', '光学损耗', '指向误差', '接收功率 P_R'};
x_pos = 0:length(labels)-1;

% 累计电平
levels = [
    P_T_dbm;
    P_T_dbm - atm_loss_db;
    P_T_dbm - atm_loss_db - abs(L_geo_dB_now);
    P_T_dbm - atm_loss_db - abs(L_geo_dB_now) - opt_db;
    P_T_dbm - atm_loss_db - abs(L_geo_dB_now) - opt_db - pnt_db;
    P_R_dbm
];

bar_colors = [
    0.082 0.396 0.753;    % P_T — 蓝
    0.776 0.157 0.157;    % 大气衰减 — 红
    0.902 0.196 0.0;      % 几何损耗 — 深橙
    0.957 0.486 0.0;      % 光学损耗 — 橙
    0.984 0.549 0.0;      % 指向误差 — 浅橙
    0.180 0.490 0.196     % P_R — 绿
];

y_min_display = min(sensitivity - 6, P_R_dbm - 4);

for i = 1:length(labels)
    if i == 1
        % 发射功率
        bottom = y_min_display;
        height = P_T_dbm - y_min_display;
        bar(x_pos(i), height, 0.55, 'FaceColor', bar_colors(i,:), 'FaceAlpha', 0.85, 'DisplayName', legend_labels{i});
        hold on;
    elseif i == length(labels)
        % 接收功率
        bottom = y_min_display;
        height = P_R_dbm - y_min_display;
        bar(x_pos(i), height, 0.55, 'FaceColor', bar_colors(i,:), 'FaceAlpha', 0.85, 'DisplayName', legend_labels{i});
    else
        % 损耗条
        top = levels(i-1);
        bottom = levels(i);
        height = top - bottom;
        bar(x_pos(i), -height, 0.55, 'BaseValue', top, 'FaceColor', bar_colors(i,:), 'FaceAlpha', 0.82, 'DisplayName', legend_labels{i});
        % 连接线
        plot([x_pos(i)-0.5, x_pos(i)-0.275], [bottom, bottom], '--', ...
            'Color', [0.4 0.4 0.4], 'LineWidth', 0.8, 'HandleVisibility', 'off');
    end
end

% 数值标注
value_labels = {
    sprintf('%.1f dBm', P_T_dbm);
    sprintf('−%.1f dB', atm_loss_db);
    sprintf('−%.1f dB', abs(L_geo_dB_now));
    sprintf('−%.1f dB', opt_db);
    sprintf('−%.1f dB', pnt_db);
    sprintf('%.1f dBm', P_R_dbm)
};
for i = 1:length(labels)
    if i == 1
        y_txt = P_T_dbm + 0.5;
    elseif i == length(labels)
        y_txt = P_R_dbm + 0.5;
    else
        y_txt = levels(i-1) + 0.5;
    end
    text(x_pos(i), y_txt, value_labels{i}, 'HorizontalAlignment', 'center', ...
        'VerticalAlignment', 'bottom', 'FontSize', 8.5, 'Color', [0.2 0.2 0.2], ...
        'FontWeight', 'bold');
end

% 灵敏度线
yline(sensitivity, '--', 'Color', [0.776 0.157 0.157], 'LineWidth', 1.5, ...
    'DisplayName', sprintf('接收机灵敏度  %.1f dBm', sensitivity));

% 链路余量阴影
if P_R_dbm > sensitivity
    fill([x_pos(end)-0.3, x_pos(end)+0.8, x_pos(end)+0.8, x_pos(end)-0.3], ...
         [sensitivity, sensitivity, P_R_dbm, P_R_dbm], ...
         [0.180 0.490 0.196], 'FaceAlpha', 0.10, 'EdgeColor', 'none');
    annotation('doublearrow', [0.78 0.78], ...
        [ (P_R_dbm - y_min_display + 2)/(P_T_dbm - y_min_display + 6), ...
          (sensitivity - y_min_display + 2)/(P_T_dbm - y_min_display + 6) ], ...
        'Color', [0.180 0.490 0.196], 'LineWidth', 1.5);
    text(length(labels)-0.3, (P_R_dbm + sensitivity)/2, sprintf('余量\n%.1f dB', margin), ...
        'HorizontalAlignment', 'left', 'VerticalAlignment', 'middle', ...
        'FontSize', 8.5, 'Color', [0.180 0.490 0.196], 'FontWeight', 'bold');
end

set(gca, 'XTick', x_pos, 'XTickLabel', labels, 'FontSize', 9);
ylabel('功率电平 (dBm)', 'FontSize', 10);
title(sprintf('链路预算瀑布图  (距离=%.1f km, λ=%.0f nm)', distance_km, lambda_nm), ...
    'FontSize', 12, 'FontWeight', 'bold');
xlim([-0.6, length(labels)-0.3]);
y_top = P_T_dbm + 4;
ylim([y_min_display - 2, y_top]);
legend('Location', 'northeast', 'FontSize', 9);
grid on; box off;

%% =======================================================================
%  辅助函数: Gauss-Hermite 求积
%% =======================================================================
function [x, w] = hermite_gauss(n)
    i = 1:n-1;
    beta = sqrt(i/2);
    T = diag(beta, 1) + diag(beta, -1);
    [V, D] = eig(T);
    x = diag(D);
    w = sqrt(pi) * V(1,:).^2;
    [x, idx] = sort(x);
    w = w(idx);
    x = x(:);   % 确保为列向量，与 Python hermgauss 一致
    w = w(:);   % 确保为列向量
end

%% =======================================================================
%  完成提示
%% =======================================================================
fprintf('============================================================\n');
fprintf('  8 张验证图表已生成，与 Python 项目一一对应:\n');
fprintf('  1. 大气衰减 vs 距离\n');
fprintf('  2. 闪烁指数 vs 距离\n');
fprintf('  3. 接收功率 vs 距离\n');
fprintf('  4. 噪声分析饼图\n');
fprintf('  5. BER vs SNR — AWGN 信道\n');
fprintf('  6. BER vs SNR — 湍流信道\n');
fprintf('  7. 光强概率密度分布\n');
fprintf('  8. 链路预算瀑布图\n');
fprintf('============================================================\n');
